"""
Vector Database Handler for YouTube Semantic Search

This module provides a clean interface for interacting with ChromaDB
to store and retrieve video metadata, transcripts, and embeddings.
"""

import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path
import sys

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from config import VECTOR_DB_PATH, COLLECTION_NAME, DISTANCE_METRIC


class VideoVectorDB:
    """
    Manages ChromaDB collection for YouTube video semantic search.
    
    Stores:
    - Video metadata (id, title, channel, views, duration, etc.)
    - Full transcripts
    - Sentence embeddings (384-dim vectors)
    """
    
    def __init__(self, persist_directory: str = VECTOR_DB_PATH, 
                 collection_name: str = COLLECTION_NAME):
        """
        Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Path to store ChromaDB data
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get existing collection or create a new one."""
        # Use ChromaDB's built-in get_or_create_collection method
        collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": DISTANCE_METRIC}
        )
        
        # Check if collection already had data
        count = collection.count()
        if count > 0:
            print(f"✓ Loaded existing collection: {self.collection_name} ({count} videos)")
        else:
            print(f"✓ Created new collection: {self.collection_name}")
        
        return collection
    
    def insert_videos(self, 
                     video_ids: List[str],
                     transcripts: List[str],
                     embeddings: np.ndarray,
                     metadata: List[Dict]) -> None:
        """
        Insert multiple videos into the collection.
        
        Args:
            video_ids: List of YouTube video IDs
            transcripts: List of full video transcripts
            embeddings: Numpy array of embeddings (n_videos, embedding_dim)
            metadata: List of dicts containing video metadata
                     (title, channel_title, view_count, duration_seconds, etc.)
        """
        # Convert numpy array to list for ChromaDB
        embeddings_list = embeddings.tolist()
        
        # Add videos to collection
        self.collection.add(
            ids=video_ids,
            documents=transcripts,
            embeddings=embeddings_list,
            metadatas=metadata
        )
        
        print(f"✓ Inserted {len(video_ids)} videos into {self.collection_name}")
    
    def search_videos(self, 
                     query_embedding: np.ndarray,
                     top_k: int = 5,
                     metadata_filter: Optional[Dict] = None) -> Tuple[List[str], List[float], List[Dict]]:
        """
        Search for similar videos using query embedding.
        
        Args:
            query_embedding: Query embedding vector (1D numpy array)
            top_k: Number of results to return
            metadata_filter: Optional filter dict (e.g., {"view_count": {"$gte": 10000}})
        
        Returns:
            Tuple of (video_ids, distances, metadata)
        """
        # Convert to list and ensure 2D shape for ChromaDB
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        query_list = query_embedding.tolist()
        
        # Perform search
        results = self.collection.query(
            query_embeddings=query_list,
            n_results=top_k,
            where=metadata_filter,
            include=["metadatas", "distances"]
        )
        
        # Extract results
        video_ids = results['ids'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        
        return video_ids, distances, metadatas
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """
        Retrieve a specific video by ID.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with video data or None if not found
        """
        try:
            result = self.collection.get(
                ids=[video_id],
                include=["metadatas", "documents", "embeddings"]
            )
            
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'transcript': result['documents'][0],
                    'embedding': np.array(result['embeddings'][0]),
                    'metadata': result['metadatas'][0]
                }
            return None
        except Exception as e:
            print(f"Error retrieving video {video_id}: {e}")
            return None
    
    def update_video(self, video_id: str, 
                    transcript: Optional[str] = None,
                    embedding: Optional[np.ndarray] = None,
                    metadata: Optional[Dict] = None) -> bool:
        """
        Update an existing video's data.
        
        Args:
            video_id: YouTube video ID
            transcript: New transcript (optional)
            embedding: New embedding vector (optional)
            metadata: New metadata dict (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            update_dict = {"ids": [video_id]}
            
            if transcript is not None:
                update_dict["documents"] = [transcript]
            if embedding is not None:
                update_dict["embeddings"] = [embedding.tolist()]
            if metadata is not None:
                update_dict["metadatas"] = [metadata]
            
            self.collection.update(**update_dict)
            print(f"✓ Updated video: {video_id}")
            return True
        except Exception as e:
            print(f"Error updating video {video_id}: {e}")
            return False
    
    def delete_video(self, video_id: str) -> bool:
        """
        Delete a video from the collection.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[video_id])
            print(f"✓ Deleted video: {video_id}")
            return True
        except Exception as e:
            print(f"Error deleting video {video_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection stats
        """
        count = self.collection.count()
        
        return {
            'total_videos': count,
            'collection_name': self.collection_name,
            'persist_directory': self.persist_directory,
            'distance_metric': DISTANCE_METRIC
        }
    
    def clear_collection(self) -> bool:
        """
        Delete all videos from collection (use with caution!).
        
        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self._get_or_create_collection()
            print(f"✓ Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False


def initialize_collection(persist_directory: str = VECTOR_DB_PATH,
                         collection_name: str = COLLECTION_NAME) -> VideoVectorDB:
    """
    Convenience function to initialize the vector database.
    
    Args:
        persist_directory: Path to store ChromaDB data
        collection_name: Name of the collection
    
    Returns:
        VideoVectorDB instance
    """
    return VideoVectorDB(persist_directory, collection_name)


if __name__ == "__main__":
    # Test the database handler
    print("=" * 60)
    print("Testing Vector Database Handler")
    print("=" * 60)
    
    # Initialize database
    db = initialize_collection()
    
    # Get stats
    stats = db.get_collection_stats()
    print(f"\n📊 Collection Stats:")
    for key, value in stats.items():
        print(f"   • {key}: {value}")
    
    print("\n✅ Database handler initialized successfully!")
