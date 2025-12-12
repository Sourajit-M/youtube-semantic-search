# config.py
import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"

# YouTube API Configuration
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', 'your_key_here')
CHANNEL_ID = 'UCX6b17PVsYBQ0ip5gyeme-Q'  # CrashCourse channel

# Vector Database Configuration
VECTOR_DB_PATH = str(DATA_DIR / "vectordb")
COLLECTION_NAME = "youtube_videos"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2
DISTANCE_METRIC = "cosine"  # Options: cosine, l2, ip

if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == 'your_key_here':
    print("⚠️  Warning: YOUTUBE_API_KEY not set. Set it in .env or environment.")
