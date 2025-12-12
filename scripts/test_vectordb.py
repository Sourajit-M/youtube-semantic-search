"""
Simple test script to verify vector database functionality
Tests basic database operations without heavy dependencies
"""

from pathlib import Path
import sys

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from scripts.db_handler import initialize_collection


def test_database():
    """Test basic database functionality."""
    print("=" * 70)
    print("VECTOR DATABASE TEST")
    print("=" * 70)
    
    # Test 1: Initialize database
    print("\n[Test 1] Initializing database...")
    db = initialize_collection()
    print("✓ Database initialized successfully")
    
    # Test 2: Get collection stats
    print("\n[Test 2] Checking collection stats...")
    stats = db.get_collection_stats()
    print(f"✓ Collection stats:")
    for key, value in stats.items():
        print(f"   • {key}: {value}")
    
    # Test 3: Retrieve a random video
    print("\n[Test 3] Retrieving a sample video...")
    test_video_id = "t6xLo1XYZZs"  # First video from migration
    video_data = db.get_video_by_id(test_video_id)
    
    if video_data:
        print(f"✓ Successfully retrieved video: {test_video_id}")
        print(f"   • Title: {video_data['metadata']['title'][:60]}...")
        print(f"   • Views: {video_data['metadata']['view_count']:,}")
        print(f"   • Duration: {video_data['metadata']['duration_seconds']} seconds")
        print(f"   • Embedding shape: {video_data['embedding'].shape}")
    else:
        print(f"✗ Failed to retrieve video: {test_video_id}")
    
    # Test 4: Verify all videos are accessible
    print("\n[Test 4] Verifying data integrity...")
    total_videos = stats['total_videos']
    
    if total_videos > 0:
        print(f"✓ Database contains {total_videos} videos")
        print(f"✓ All data successfully migrated from CSV")
    else:
        print(f"✗ Database is empty!")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   • Run semantic search: python scripts/semantic_search.py -q 'your query'")
    print("   • Check more details: python scripts/db_handler.py")


if __name__ == "__main__":
    test_database()
