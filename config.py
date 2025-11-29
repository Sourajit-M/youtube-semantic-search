# config.py
import os
from dotenv import load_dotenv

# Load .env (YOUTUBE_API_KEY, CHANNEL_ID)
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "UCX6b17PVsYBQ0ip5gyeme-Q")  # CrashCourse default

if not YOUTUBE_API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY not set. Put it in .env or environment.")
