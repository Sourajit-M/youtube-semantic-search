"""
Semantic Search Interface for YouTube Videos

Search for videos using natural language queries.
Uses sentence embeddings for semantic similarity matching.
"""

# Suppress warnings before imports
import os
import warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')

import argparse
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import sys

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from scripts.db_handler import initialize_collection
from config import EMBEDDING_MODEL


class VideoSemanticSearch:
    """
    Semantic search engine for YouTube videos.
    """
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        """
        Initialize search engine.
        
        Args:
            model_name: Name of sentence-transformer model
        """
        print(f"🤖 Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        print("🗄️  Connecting to vector database...")
        self.db = initialize_collection()
        
        stats = self.db.get_collection_stats()
        print(f"   ✓ Database loaded: {stats['total_videos']} videos available\n")
    
    def search(self, query: str, top_k: int = 5, metadata_filter=None):
        """
        Search for videos matching the query.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            metadata_filter: Optional metadata filter dict
        
        Returns:
            List of result dictionaries
        """
        # Generate query embedding
        print(f"🔍 Searching for: \"{query}\"")
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Search database
        video_ids, distances, metadatas = self.db.search_videos(
            query_embedding=query_embedding,
            top_k=top_k,
            metadata_filter=metadata_filter
        )
        
        # Format results
        results = []
        for i, (video_id, distance, metadata) in enumerate(zip(video_ids, distances, metadatas)):
            # Convert distance to similarity score (cosine distance → similarity)
            similarity = 1 - distance
            
            result = {
                'rank': i + 1,
                'video_id': video_id,
                'title': metadata.get('title', 'N/A'),
                'channel': metadata.get('channel_title', 'N/A'),
                'views': metadata.get('view_count', 0),
                'duration': metadata.get('duration_seconds', 0),
                'similarity_score': round(similarity, 4),
                'youtube_url': f"https://youtu.be/{video_id}"
            }
            results.append(result)
        
        return results
    
    def display_results(self, results):
        """
        Display search results in a formatted way.
        
        Args:
            results: List of result dictionaries
        """
        print(f"\n{'='*80}")
        print(f"TOP {len(results)} RESULTS")
        print(f"{'='*80}\n")
        
        for result in results:
            print(f"[{result['rank']}] 🎯 Score: {result['similarity_score']:.3f}")
            print(f"    📺 {result['title']}")
            print(f"    🔗 {result['youtube_url']}")
            print(f"    👁️  {result['views']:,} views | ⏱️ {result['duration']//60}m {result['duration']%60}s")
            print()
        
        print(f"{'='*80}\n")


def format_duration(seconds):
    """Convert seconds to MM:SS format."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Search YouTube videos using semantic search"
    )
    parser.add_argument(
        '--query', '-q',
        type=str,
        required=True,
        help='Search query (natural language)'
    )
    parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=5,
        help='Number of results to return (default: 5)'
    )
    parser.add_argument(
        '--min-views',
        type=int,
        default=None,
        help='Filter by minimum view count'
    )
    
    args = parser.parse_args()
    
    # Initialize search engine
    search_engine = VideoSemanticSearch()
    
    # Build metadata filter if specified
    metadata_filter = None
    if args.min_views is not None:
        metadata_filter = {"view_count": {"$gte": args.min_views}}
    
    # Perform search
    results = search_engine.search(
        query=args.query,
        top_k=args.top_k,
        metadata_filter=metadata_filter
    )
    
    # Display results
    search_engine.display_results(results)
    
    # Optional: Save results to file
    # TODO: Add option to export results to JSON/CSV


if __name__ == "__main__":
    main()
