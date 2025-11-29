# scripts/extract_videos.py
"""
STEP 1: Extract complete video metadata for CrashCourse (or any channel)

- Uses channel's 'uploads' playlist to get ALL public uploads
- Fetches:
    id, title, description, publishedAt, tags, categoryId,
    defaultLanguage, defaultAudioLanguage,
    thumbnail_default, thumbnail_high,
    duration, viewCount, likeCount, commentCount, privacyStatus,
    channel_id, channel_title,
    channel_description, channel_country, channel_thumbnail,
    channel_subscriberCount, channel_videoCount

Output:
    data/crashcourse_metadata.csv
"""

import os
import sys
import time
import argparse
from pathlib import Path

import pandas as pd
from googleapiclient.discovery import build

# Allow import of config from project root
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
from config import YOUTUBE_API_KEY, CHANNEL_ID  # type: ignore


# --------------------------------------------------------------------
# Helper: YouTube client
# --------------------------------------------------------------------
def get_youtube():
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# --------------------------------------------------------------------
# 1) Get uploads playlist ID
# --------------------------------------------------------------------
def get_uploads_playlist_id(youtube, channel_id: str) -> str:
    resp = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    ).execute()

    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"No channel found for id={channel_id}")

    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Uploads playlist ID: {uploads_playlist_id}")
    return uploads_playlist_id


# --------------------------------------------------------------------
# 2) Get video IDs from uploads playlist
# --------------------------------------------------------------------
def get_video_ids(youtube, channel_id: str, target_count: int = 250):
    print("Step 1: Fetching video IDs from uploads playlist...")

    uploads_playlist_id = get_uploads_playlist_id(youtube, channel_id)

    video_ids = []
    next_page_token = None

    while len(video_ids) < target_count:
        req = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        res = req.execute()

        for item in res.get("items", []):
            vid = item["contentDetails"]["videoId"]
            video_ids.append(vid)

        print(f"  Collected {len(video_ids)} video IDs...", end="\r")

        if len(video_ids) >= target_count:
            break

        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(0.2)

    video_ids = video_ids[:target_count]
    print(f"\nCollected {len(video_ids)} video IDs\n")
    return video_ids


# --------------------------------------------------------------------
# 3) Get full video metadata via videos.list
# --------------------------------------------------------------------
def get_video_details(youtube, video_ids):
    print("Step 2: Fetching complete metadata...")

    all_rows = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]

        req = youtube.videos().list(
            part="snippet,contentDetails,statistics,status",
            id=",".join(batch)
        )
        res = req.execute()

        for item in res.get("items", []):
            snip = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            status = item.get("status", {})

            row = {
                "id": item.get("id"),
                "title": snip.get("title"),
                "description": snip.get("description"),
                "publishedAt": snip.get("publishedAt"),
                "tags": ", ".join(snip.get("tags", [])),
                "categoryId": snip.get("categoryId"),
                "defaultLanguage": snip.get("defaultLanguage", ""),
                "defaultAudioLanguage": snip.get("defaultAudioLanguage", ""),
                "thumbnail_default": snip.get("thumbnails", {}).get("default", {}).get("url"),
                "thumbnail_high": snip.get("thumbnails", {}).get("high", {}).get("url"),
                "duration": content.get("duration"),
                "viewCount": int(stats.get("viewCount", 0)) if stats.get("viewCount") is not None else 0,
                "likeCount": int(stats.get("likeCount", 0)) if stats.get("likeCount") is not None else 0,
                "commentCount": int(stats.get("commentCount", 0)) if stats.get("commentCount") is not None else 0,
                "privacyStatus": status.get("privacyStatus", ""),
                "channel_id": snip.get("channelId"),
                "channel_title": snip.get("channelTitle"),
                # channel_* fields will be filled later
                "channel_description": None,
                "channel_country": None,
                "channel_thumbnail": None,
                "channel_subscriberCount": None,
                "channel_videoCount": None,
            }
            all_rows.append(row)

        print(f"  Processed {len(all_rows)}/{len(video_ids)} videos...", end="\r")
        time.sleep(0.2)

    print(f"\nFetched metadata for {len(all_rows)} videos\n")
    return pd.DataFrame(all_rows)


# --------------------------------------------------------------------
# 4) Enrich channel metadata
# --------------------------------------------------------------------
def enrich_channel_details(youtube, df: pd.DataFrame) -> pd.DataFrame:
    print("Step 3: Enriching channel metadata...")

    unique_channels = df["channel_id"].dropna().unique()
    if len(unique_channels) == 0:
        print("No channel IDs found in data.")
        return df

    channel_info = {}

    for i in range(0, len(unique_channels), 50):
        chunk = unique_channels[i:i + 50]
        req = youtube.channels().list(
            part="snippet,statistics",
            id=",".join(chunk)
        )
        res = req.execute()

        for ch in res.get("items", []):
            snip = ch.get("snippet", {})
            stats = ch.get("statistics", {})
            channel_info[ch["id"]] = {
                "channel_description": snip.get("description"),
                "channel_country": snip.get("country"),
                "channel_thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url"),
                "channel_subscriberCount": int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") is not None else 0,
                "channel_videoCount": int(stats.get("videoCount", 0)) if stats.get("videoCount") is not None else 0,
            }

        time.sleep(0.2)

    for ch_id, info in channel_info.items():
        for col, val in info.items():
            df.loc[df["channel_id"] == ch_id, col] = val

    print("Channel metadata enriched\n")
    return df


# --------------------------------------------------------------------
# 5) Summary + save
# --------------------------------------------------------------------
def display_summary(df: pd.DataFrame):
    print("DATASET SUMMARY")

    df["publishedAt"] = pd.to_datetime(df["publishedAt"])

    print(f"\nTotal Videos: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Date Range: {df['publishedAt'].min().date()} to {df['publishedAt'].max().date()}")

    print(f"\nAll Columns ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\nSample Videos (First 3):")
    for idx, row in df.head(3).iterrows():
        print(f"\n{idx+1}. {row['title'][:60]}...")
        print(f"   ID: {row['id']}")
        print(f"   Views: {row['viewCount']:,} | Likes: {row['likeCount']:,}")
        print(f"   Duration: {row['duration']} | Date: {row['publishedAt'].date()}")


def save_metadata(df: pd.DataFrame, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Metadata saved to: {output_path}")


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Extract complete CrashCourse video metadata")
    parser.add_argument("--channel-id", default=CHANNEL_ID, help="YouTube channel ID")
    parser.add_argument("--max-videos", type=int, default=250, help="Max videos to fetch")
    parser.add_argument("--output", default="data/crashcourse_metadata.csv", help="Output CSV path")
    args = parser.parse_args()

    print("CRASHCOURSE COMPLETE METADATA EXTRACTION")

    youtube = get_youtube()

    video_ids = get_video_ids(youtube, args.channel_id, args.max_videos)
    if not video_ids:
        print("No video IDs fetched.")
        return

    df = get_video_details(youtube, video_ids)
    if df.empty:
        print("No metadata extracted.")
        return

    df = enrich_channel_details(youtube, df)
    display_summary(df)
    save_metadata(df, Path(args.output))

    print("\nCOMPLETE!")
    print(f"-Extracted {len(df)} videos with {len(df.columns)} columns")
    print("\nNext: run scripts/extract_transcripts.py to add transcripts.\n")


if __name__ == "__main__":
    main()
