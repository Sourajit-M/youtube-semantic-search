"""
Data Migration Script: CSV to ChromaDB

Migrates YouTube video data from crashcourse_final.csv to ChromaDB vector database.
Handles: video metadata, transcripts, and embeddings.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys
from tqdm import tqdm

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from scripts.db_handler import initialize_collection
from config import DATA_DIR


def parse_embedding_string(embedding_str):
    """
    Parse embedding from JSON string to numpy array.
    
    Args:
        embedding_str: JSON string representation of embedding
    
    Returns:
        numpy array of shape (embedding_dim,)
    """
    try:
        embedding_list = json.loads(embedding_str)
        return np.array(embedding_list, dtype=np.float32)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing embedding: {e}")
        return None


def load_csv_data(csv_path):
    """
    Load video data from CSV file.
    
    Args:
        csv_path: Path to crashcourse_final.csv
    
    Returns:
        pandas DataFrame
    """
    print(f"\n📂 Loading data from: {csv_path.name}")
    df = pd.read_csv(csv_path)
    print(f"   ✓ Loaded {len(df)} videos")
    return df


def prepare_data_for_db(df):
    """
    Prepare data from DataFrame for ChromaDB insertion.
    
    Args:
        df: pandas DataFrame with video data
    
    Returns:
        Tuple of (video_ids, transcripts, embeddings, metadata_list)
    """
    print("\n🔧 Preparing data for ChromaDB...")
    
    video_ids = []
    transcripts = []
    embeddings_list = []
    metadata_list = []
    
    failed_count = 0
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing videos"):
        # Parse embedding
        embedding = parse_embedding_string(row['embeddings'])
        
        if embedding is None:
            failed_count += 1
            continue
        
        # Extract video ID (use 'id' column from CSV)
        video_id = str(row['id'])
        
        # Extract transcript
        transcript = str(row['transcript']) if pd.notna(row['transcript']) else ""
        
        # Build metadata dictionary
        metadata = {
            'title': str(row['title']) if pd.notna(row['title']) else "",
            'channel_title': str(row['channel_title']) if pd.notna(row['channel_title']) else "",
            'view_count': int(row['viewCount']) if pd.notna(row['viewCount']) else 0,
            'duration_seconds': int(row['duration_seconds']) if pd.notna(row['duration_seconds']) else 0,
            'published_at': str(row['publishedAt']) if pd.notna(row['publishedAt']) else "",
            'like_count': int(row['likeCount']) if pd.notna(row['likeCount']) else 0,
            'comment_count': int(row['commentCount']) if pd.notna(row['commentCount']) else 0,
        }
        
        video_ids.append(video_id)
        transcripts.append(transcript)
        embeddings_list.append(embedding)
        metadata_list.append(metadata)
    
    # Convert embeddings list to numpy array
    embeddings_array = np.array(embeddings_list, dtype=np.float32)
    
    print(f"   ✓ Successfully prepared {len(video_ids)} videos")
    if failed_count > 0:
        print(f"   ⚠️  Failed to parse {failed_count} embeddings")
    
    return video_ids, transcripts, embeddings_array, metadata_list


def verify_migration(db, expected_count):
    """
    Verify that migration was successful.
    
    Args:
        db: VideoVectorDB instance
        expected_count: Expected number of videos
    
    Returns:
        bool: True if verification passed
    """
    print("\n🔍 Verifying migration...")
    
    stats = db.get_collection_stats()
    actual_count = stats['total_videos']
    
    if actual_count == expected_count:
        print(f"   ✓ Verification passed: {actual_count} videos in database")
        return True
    else:
        print(f"   ✗ Verification failed: Expected {expected_count}, found {actual_count}")
        return False


def generate_migration_report(video_ids, stats):
    """
    Generate a summary report of the migration.
    
    Args:
        video_ids: List of migrated video IDs
        stats: Collection stats from database
    """
    print("\n" + "=" * 70)
    print("MIGRATION REPORT")
    print("=" * 70)
    
    print(f"\n📊 Summary:")
    print(f"   • Total videos migrated: {len(video_ids)}")
    print(f"   • Collection name: {stats['collection_name']}")
    print(f"   • Storage location: {stats['persist_directory']}")
    print(f"   • Distance metric: {stats['distance_metric']}")
    
    print(f"\n✅ Sample video IDs (first 5):")
    for vid in video_ids[:5]:
        print(f"   • {vid}")
    
    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)


def main():
    """Main migration execution."""
    print("=" * 70)
    print("CSV TO CHROMADB MIGRATION")
    print("=" * 70)
    
    # Define paths
    csv_path = Path(DATA_DIR) / "crashcourse_final.csv"
    
    # Check if CSV exists
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        print(f"   Please ensure crashcourse_final.csv exists in the data directory.")
        return
    
    # Step 1: Load CSV data
    df = load_csv_data(csv_path)
    
    # Step 2: Prepare data for ChromaDB
    video_ids, transcripts, embeddings, metadata_list = prepare_data_for_db(df)
    
    if len(video_ids) == 0:
        print("❌ No valid data to migrate. Exiting.")
        return
    
    # Step 3: Initialize ChromaDB
    print("\n🗄️  Initializing ChromaDB...")
    db = initialize_collection()
    
    # Step 4: Insert data into ChromaDB
    print(f"\n💾 Inserting {len(video_ids)} videos into ChromaDB...")
    db.insert_videos(
        video_ids=video_ids,
        transcripts=transcripts,
        embeddings=embeddings,
        metadata=metadata_list
    )
    
    # Step 5: Verify migration
    verification_passed = verify_migration(db, len(video_ids))
    
    # Step 6: Generate report
    if verification_passed:
        stats = db.get_collection_stats()
        generate_migration_report(video_ids, stats)
    else:
        print("\n❌ Migration verification failed. Please check the database.")
    
    print("\n💡 Next steps:")
    print("   • Test semantic search with: python scripts/semantic_search.py")
    print("   • View database stats with: python scripts/db_handler.py")


if __name__ == "__main__":
    main()
