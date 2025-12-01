# scripts/extract_videos_with_transcripts.py
"""
Combined script to extract YouTube videos with transcripts.

This script fetches videos from a YouTube channel and extracts their transcripts,
stopping when the target number of videos with successful transcripts is reached.

Usage:
    python scripts/extract_videos_with_transcripts.py --target-transcripts 50

Output:
    data/crashcourse_videos.csv    (videos with transcripts)
    data/failed_transcripts.txt    (log of failures)
"""

import os
import sys
import time
import argparse
import glob
import shutil
from pathlib import Path

import pandas as pd
import webvtt
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL

# Allow import of config from project root
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
from config import YOUTUBE_API_KEY, CHANNEL_ID  # type: ignore


# --------------------------------------------------------------------
# YouTube Client
# --------------------------------------------------------------------
def get_youtube():
    """Initialize YouTube API client."""
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# --------------------------------------------------------------------
# Get uploads playlist ID
# --------------------------------------------------------------------
def get_uploads_playlist_id(youtube, channel_id: str) -> str:
    """Get the uploads playlist ID for a channel."""
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
# Fetch transcript for a single video
# --------------------------------------------------------------------
def fetch_transcript(video_id: str, languages=None) -> str | None:
    """
    Fetch transcript for a video using yt-dlp.
    Returns transcript text or None if unavailable.
    """
    if languages is None:
        languages = ["en"]

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': languages,
        'outtmpl': f'temp_subs/{video_id}',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Clean up temp dir if exists
        if os.path.exists('temp_subs'):
            shutil.rmtree('temp_subs')
        os.makedirs('temp_subs', exist_ok=True)

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

        # Find the downloaded vtt file
        vtt_files = glob.glob(f'temp_subs/{video_id}*.vtt')
        if not vtt_files:
            return None

        # Parse the VTT file
        vtt_file = vtt_files[0]
        text_parts = []
        seen_lines = set()

        for caption in webvtt.read(vtt_file):
            line = caption.text.strip().replace('\n', ' ')
            if line and line not in seen_lines:
                text_parts.append(line)
                seen_lines.add(line)

        full_text = " ".join(text_parts)

        # Cleanup
        shutil.rmtree('temp_subs')

        return full_text.strip() if full_text.strip() else None

    except Exception as e:
        print(f"  Warning: error fetching transcript for {video_id}: {e}")
        if os.path.exists('temp_subs'):
            shutil.rmtree('temp_subs')
        return None


# --------------------------------------------------------------------
# Get video metadata for a batch of IDs
# --------------------------------------------------------------------
def get_video_metadata(youtube, video_ids: list) -> list[dict]:
    """Fetch metadata for a batch of video IDs."""
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
                "viewCount": int(stats.get("viewCount", 0)) if stats.get("viewCount") else 0,
                "likeCount": int(stats.get("likeCount", 0)) if stats.get("likeCount") else 0,
                "commentCount": int(stats.get("commentCount", 0)) if stats.get("commentCount") else 0,
                "privacyStatus": status.get("privacyStatus", ""),
                "channel_id": snip.get("channelId"),
                "channel_title": snip.get("channelTitle"),
                "channel_description": None,
                "channel_country": None,
                "channel_thumbnail": None,
                "channel_subscriberCount": None,
                "channel_videoCount": None,
            }
            all_rows.append(row)

    return all_rows


# --------------------------------------------------------------------
# Enrich channel metadata
# --------------------------------------------------------------------
def enrich_channel_details(youtube, df: pd.DataFrame) -> pd.DataFrame:
    """Add channel metadata to the dataframe."""
    print("\nEnriching channel metadata...")

    unique_channels = df["channel_id"].dropna().unique()
    if len(unique_channels) == 0:
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
                "channel_subscriberCount": int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") else 0,
                "channel_videoCount": int(stats.get("videoCount", 0)) if stats.get("videoCount") else 0,
            }

    for ch_id, info in channel_info.items():
        for col, val in info.items():
            df.loc[df["channel_id"] == ch_id, col] = val

    print("Channel metadata enriched")
    return df


# --------------------------------------------------------------------
# Main extraction function
# --------------------------------------------------------------------
def fetch_videos_with_transcripts(youtube, channel_id: str, target_count: int, delay: float = 0.5):
    """
    Fetch videos until we have target_count with successful transcripts.
    
    Args:
        youtube: YouTube API client
        channel_id: YouTube channel ID
        target_count: Number of videos with transcripts to collect
        delay: Delay between transcript fetches (seconds)
    
    Returns:
        tuple: (DataFrame of successful videos, list of failed videos)
    """
    print("=" * 70)
    print("YOUTUBE VIDEO + TRANSCRIPT EXTRACTION")
    print("=" * 70)
    print(f"\nTarget: {target_count} videos with transcripts\n")

    uploads_playlist_id = get_uploads_playlist_id(youtube, channel_id)

    successful_videos = []
    failed_videos = []
    next_page_token = None
    total_processed = 0

    while len(successful_videos) < target_count:
        # Fetch batch of video IDs
        print(f"\nFetching next batch of video IDs...")
        req = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        res = req.execute()

        batch_ids = [item["contentDetails"]["videoId"] for item in res.get("items", [])]

        if not batch_ids:
            print("No more videos available in channel")
            break

        # Get metadata for this batch
        print(f"Fetching metadata for {len(batch_ids)} videos...")
        batch_metadata = get_video_metadata(youtube, batch_ids)

        # Process each video
        for video in batch_metadata:
            total_processed += 1
            vid = video["id"]
            title = video.get("title", "")[:50]

            print(f"[{len(successful_videos)}/{target_count}] Processing {vid} - {title}...", end=" ")

            # Try to fetch transcript
            transcript = fetch_transcript(vid)

            if transcript:
                video["transcript"] = transcript
                successful_videos.append(video)
                print("✓ OK")

                if len(successful_videos) >= target_count:
                    print(f"\n✓ Reached target of {target_count} videos with transcripts!")
                    break
            else:
                failed_videos.append({"video_id": vid, "title": video.get("title", "")})
                print("✗ FAILED")

            time.sleep(delay)

        # Get next page token for more videos
        next_page_token = res.get("nextPageToken")
        if not next_page_token and len(successful_videos) < target_count:
            print("\nNo more videos available in channel")
            break

    print(f"\n" + "=" * 70)
    print(f"EXTRACTION COMPLETE")
    print(f"=" * 70)
    print(f"Total videos processed: {total_processed}")
    print(f"Successful (with transcript): {len(successful_videos)}")
    print(f"Failed (no transcript): {len(failed_videos)}")

    return pd.DataFrame(successful_videos), failed_videos


# --------------------------------------------------------------------
# Log failures
# --------------------------------------------------------------------
def log_failures(failed: list, log_path: Path):
    """Write failed transcript extractions to log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("FAILED TRANSCRIPT EXTRACTIONS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total Failed: {len(failed)}\n\n")
        for item in failed:
            vid = item["video_id"]
            f.write(f"Video ID: {vid}\n")
            f.write(f"Title: {item['title']}\n")
            f.write(f"URL: https://www.youtube.com/watch?v={vid}\n")
            f.write("-" * 70 + "\n")

    print(f"Failed transcripts logged to: {log_path}")


# --------------------------------------------------------------------
# Display summary
# --------------------------------------------------------------------
def display_summary(df: pd.DataFrame):
    """Display summary of the extracted dataset."""
    print("\n" + "=" * 70)
    print("DATASET SUMMARY")
    print("=" * 70)

    df["publishedAt"] = pd.to_datetime(df["publishedAt"])

    print(f"\nTotal Videos: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Date Range: {df['publishedAt'].min().date()} to {df['publishedAt'].max().date()}")

    # Transcript statistics
    df["_transcript_length"] = df["transcript"].str.len()
    df["_transcript_words"] = df["transcript"].str.split().str.len()

    print(f"\nTranscript Statistics:")
    print(f"  Average length: {df['_transcript_length'].mean():.0f} characters")
    print(f"  Average words: {df['_transcript_words'].mean():.0f}")
    print(f"  Shortest: {df['_transcript_length'].min()} chars")
    print(f"  Longest: {df['_transcript_length'].max()} chars")

    # Clean up temp columns
    df.drop(columns=["_transcript_length", "_transcript_words"], inplace=True)

    print("\nSample Videos (First 3):")
    for idx, row in df.head(3).iterrows():
        print(f"\n{idx+1}. {row['title'][:60]}...")
        print(f"   ID: {row['id']}")
        print(f"   Views: {row['viewCount']:,} | Likes: {row['likeCount']:,}")
        print(f"   Duration: {row['duration']}")
        print(f"   Transcript preview: {row['transcript'][:100]}...")


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract YouTube videos with transcripts until target count is reached"
    )
    parser.add_argument(
        "--target-transcripts",
        type=int,
        default=50,
        help="Number of videos with transcripts to collect (default: 50)"
    )
    parser.add_argument(
        "--channel-id",
        default=CHANNEL_ID,
        help="YouTube channel ID"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "data/crashcourse_videos.csv"),
        help="Output CSV path"
    )
    parser.add_argument(
        "--failed-log",
        default=str(ROOT_DIR / "data/failed_transcripts.txt"),
        help="Failed transcripts log path"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between transcript fetches in seconds (default: 0.5)"
    )
    args = parser.parse_args()

    # Initialize YouTube client
    youtube = get_youtube()

    # Fetch videos with transcripts
    df, failed = fetch_videos_with_transcripts(
        youtube,
        args.channel_id,
        args.target_transcripts,
        args.delay
    )

    if df.empty:
        print("\nNo videos with transcripts extracted.")
        return

    # Enrich with channel details
    df = enrich_channel_details(youtube, df)

    # Save dataset
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✓ Dataset saved to: {output_path}")

    # Log failures
    if failed:
        log_failures(failed, Path(args.failed_log))

    # Display summary
    display_summary(df)

    print("\n" + "=" * 70)
    print("✅ EXTRACTION COMPLETE!")
    print(f"   {len(df)} videos with transcripts saved to {args.output}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()