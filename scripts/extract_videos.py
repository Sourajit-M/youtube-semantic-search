import os
import time
from typing import List, Dict

import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # CrashCourse

# Number of most recent videos to keep
MAX_VIDEOS = 50   # change to 300/350 if you want

if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in .env")
if not CHANNEL_ID:
    raise RuntimeError("YOUTUBE_CHANNEL_ID not set in .env")

youtube = build("youtube", "v3", developerKey=API_KEY)


def get_channel_info(channel_id: str) -> Dict:
    """Get basic channel info and uploads playlist ID."""
    req = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id,
    )
    resp = req.execute()
    if not resp["items"]:
        raise RuntimeError(f"No channel found for id={channel_id}")

    item = resp["items"][0]
    uploads_playlist_id = item["contentDetails"]["relatedPlaylists"]["uploads"]

    info = {
        "channel_title": item["snippet"]["title"],
        "channel_description": item["snippet"]["description"],
        "channel_country": item["snippet"].get("country", "N/A"),
        "channel_subscriberCount": int(item["statistics"].get("subscriberCount", 0)),
        "channel_videoCount": int(item["statistics"].get("videoCount", 0)),
        "uploads_playlist_id": uploads_playlist_id,
    }
    return info


def fetch_from_uploads_playlist(playlist_id: str, max_videos: int) -> List[Dict]:
    """Fetch videos from the uploads playlist (oldest → newest, we’ll sort later)."""
    videos: List[Dict] = []
    next_page_token = None
    page = 0

    while True:
        if max_videos and len(videos) >= max_videos:
            break

        req = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        resp = req.execute()
        page += 1

        ids = []
        for item in resp.get("items", []):
            vid = item["contentDetails"]["videoId"]
            ids.append(vid)

        if not ids:
            break

        # Get detailed stats for these IDs
        vids_req = youtube.videos().list(
            part="snippet,contentDetails,statistics,status",
            id=",".join(ids),
        )
        vids_resp = vids_req.execute()

        for item in vids_resp.get("items", []):
            if max_videos and len(videos) >= max_videos:
                break

            s = item["snippet"]
            cd = item["contentDetails"]
            st = item["statistics"]
            status = item["status"]

            videos.append(
                {
                    "id": item["id"],
                    "title": s.get("title", ""),
                    "description": s.get("description", ""),
                    "publishedAt": s.get("publishedAt"),
                    "tags": ", ".join(s.get("tags", [])),
                    "categoryId": s.get("categoryId", ""),
                    "defaultLanguage": s.get("defaultLanguage", "en"),
                    "defaultAudioLanguage": s.get("defaultAudioLanguage", "en"),
                    "thumbnail_default": s.get("thumbnails", {})
                    .get("default", {})
                    .get("url", ""),
                    "thumbnail_high": s.get("thumbnails", {})
                    .get("high", {})
                    .get("url", ""),
                    "duration": cd.get("duration", ""),
                    "viewCount": int(st.get("viewCount", 0)),
                    "likeCount": int(st.get("likeCount", 0)),
                    "commentCount": int(st.get("commentCount", 0)),
                    "privacyStatus": status.get("privacyStatus", ""),
                }
            )

        print(f"Page {page}: fetched {len(ids)} videos | total so far = {len(videos)}")

        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break

        if max_videos and len(videos) >= max_videos:
            break

        time.sleep(0.2)

    return videos


def parse_duration(duration: str) -> int:
    """Convert ISO8601 duration to seconds."""
    import re

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if match:
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        return h * 3600 + m * 60 + s
    return 0


def process_video_data(videos, channel_info):
    df = pd.DataFrame(videos)

    # add channel info
    df["channel_id"] = CHANNEL_ID
    df["channel_title"] = channel_info["channel_title"]
    df["channel_description"] = channel_info["channel_description"]
    df["channel_country"] = channel_info["channel_country"]
    df["channel_subscriberCount"] = channel_info["channel_subscriberCount"]
    df["channel_videoCount"] = channel_info["channel_videoCount"]

    # convert dates
    df["publishedAt"] = pd.to_datetime(df["publishedAt"])
    df["publish_date"] = df["publishedAt"].dt.date
    df["publish_year"] = df["publishedAt"].dt.year

    # durations
    df["duration_seconds"] = df["duration"].apply(parse_duration)
    df["duration_minutes"] = df["duration_seconds"] / 60

    # url
    df["video_url"] = "https://www.youtube.com/watch?v=" + df["id"].astype(str)

    # sort newest first
    df = df.sort_values("publishedAt", ascending=False).reset_index(drop=True)

    print("DATASET SUMMARY")
    print(f"Total videos: {len(df)}")
    print(f"Date range: {df['publish_date'].min()} → {df['publish_date'].max()}")
    print(f"Total views: {df['viewCount'].sum():,}")
    print(f"Avg views/video: {df['viewCount'].mean():,.0f}")
    print(f"Avg duration: {df['duration_minutes'].mean():.1f} minutes")

    return df


# MAIN

if __name__ == "__main__":
    print("YOUTUBE VIDEO METADATA EXTRACTION")
    print("Channel: CrashCourse")

    info = get_channel_info(CHANNEL_ID)
    print(f"Channel: {info['channel_title']}")
    print(f"Total videos reported: {info['channel_videoCount']}")
    print(f"Subscribers: {info['channel_subscriberCount']:,}")
    print(f"Uploads playlist: {info['uploads_playlist_id']}\n")

    video_list = fetch_from_uploads_playlist(
        info["uploads_playlist_id"],
        max_videos=MAX_VIDEOS,
    )

    if not video_list:
        print("No videos fetched.")
    else:
        df = process_video_data(video_list, info)

        os.makedirs("data", exist_ok=True)
        out_path = "data/crashcourse_videos.csv"
        df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"\n✓ Data saved to: {out_path}")
        print("\nSample:")
        print(df[["id", "title", "publish_date"]].head())
        
    print("EXTRACTION COMPLETE!")
