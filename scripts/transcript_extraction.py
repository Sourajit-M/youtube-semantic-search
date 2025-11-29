# scripts/extract_transcripts.py
"""
STEP 2: Add transcripts to CrashCourse metadata

Input:
    data/crashcourse_metadata.csv  (from extract_videos.py)

Output:
    data/crashcourse_videos.csv           (only videos with transcripts)
    data/failed_transcripts.txt           (log of failures)
"""

import os
import time
from pathlib import Path

import pandas as pd
import glob
import shutil
import webvtt
from yt_dlp import YoutubeDL

INPUT_FILE = "data/crashcourse_metadata.csv"
OUTPUT_FILE = "data/crashcourse_videos.csv"
FAILED_LOG = "data/failed_transcripts.txt"

# --------------------------------------------------------------------
# Fetch transcript for single video
# --------------------------------------------------------------------
def fetch_transcript(video_id: str, languages=None):
    if languages is None:
        languages = ["en"]

    # Configure yt-dlp to download subtitles only
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

        # Parse the first found VTT file
        vtt_file = vtt_files[0]
        text_parts = []
        seen_lines = set()
        
        for caption in webvtt.read(vtt_file):
            # Simple deduping: skip if line is exactly same as previous
            # (VTT often repeats lines for karaoke effect or rolling captions)
            line = caption.text.strip()
            # Remove newlines within the caption block
            line = line.replace('\n', ' ')
            if line and line not in seen_lines:
                text_parts.append(line)
                seen_lines.add(line)
        
        full_text = " ".join(text_parts)
        
        # Cleanup
        shutil.rmtree('temp_subs')
        
        return full_text.strip() if full_text.strip() else None

    except Exception as e:
        print(f"  Warning: unexpected error for {video_id}: {e}")
        if os.path.exists('temp_subs'):
            shutil.rmtree('temp_subs')
        return None


# --------------------------------------------------------------------
# Extract transcripts for all videos
# --------------------------------------------------------------------
def extract_all_transcripts(df: pd.DataFrame, delay: float = 0.5) -> tuple[pd.DataFrame, list]:
    print("=" * 70)
    print("CRASHCOURSE TRANSCRIPT EXTRACTION")
    print("=" * 70 + "\n")

    transcripts = []
    failed = []

    total = len(df)
    print(f"Processing {total} videos...\n")

    for idx, row in df.iterrows():
        vid = row["id"]
        title = row.get("title", "")

        print(f"[{idx+1}/{total}] {vid} - {title[:50]}...", end=" ")

        txt = fetch_transcript(vid)
        if txt:
            transcripts.append(txt)
            print("OK")
        else:
            transcripts.append(None)
            failed.append({"video_id": vid, "title": title})
            print("FAILED")

        time.sleep(delay)

    df["transcript"] = transcripts
    return df, failed


# --------------------------------------------------------------------
# Log failures
# --------------------------------------------------------------------
def log_failures(failed: list, log_path: Path):
    if not failed:
        return

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


# --------------------------------------------------------------------
# Finalize dataset (keep only videos with transcripts)
# --------------------------------------------------------------------
def finalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    print("FINALIZING DATASET")

    original_count = len(df)
    df_final = df[df["transcript"].notna()].copy()
    removed_count = original_count - len(df_final)

    print(f"Original videos: {original_count}")
    print(f"Videos with transcripts: {len(df_final)}")
    print(f"Removed (no transcript): {removed_count}")

    if not df_final.empty:
        df_final["transcript_length"] = df_final["transcript"].str.len()
        df_final["transcript_word_count"] = df_final["transcript"].str.split().str.len()

        print("\nTranscript statistics:")
        print(f"  Average length: {df_final['transcript_length'].mean():.0f} characters")
        print(f"  Average words: {df_final['transcript_word_count'].mean():.0f}")
        print(f"  Shortest: {df_final['transcript_length'].min()} chars")
        print(f"  Longest:  {df_final['transcript_length'].max()} chars")

        df_final = df_final.drop(columns=["transcript_length", "transcript_word_count"])

    print("\nFinal columns:")
    for i, col in enumerate(df_final.columns, 1):
        print(f"  {i:2d}. {col}")

    return df_final


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
def main():
    # Load metadata
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} not found. Run extract_videos.py first.")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded metadata for {len(df)} videos with {len(df.columns)} columns\n")

    # Extract transcripts
    df_with_transcripts, failed = extract_all_transcripts(df, delay=0.5)

    # Log failures
    log_failures(failed, Path(FAILED_LOG))

    # Finalize dataset
    df_final = finalize_dataset(df_with_transcripts)

    if df_final.empty:
        print("\nNo transcripts extracted.")
        return

    # Save final dataset
    out_path = Path(OUTPUT_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(out_path, index=False)

    print(f"✓ Final dataset saved to: {out_path}")


    # Show one sample
    sample = df_final.iloc[0]
    print("\nSAMPLE VIDEO")
    print("-" * 70)
    print(f"ID: {sample['id']}")
    print(f"Title: {sample['title']}")
    print(f"Views: {sample['viewCount']:,}")
    print(f"Likes: {sample['likeCount']:,}")
    print(f"Duration: {sample['duration']}")
    print(f"Date: {sample['publishedAt']}")
    print("\nTranscript preview:")
    print(sample['transcript'][:300] + "...")
    print("\n✅ STEP 2 COMPLETE! You now have a clean dataset with metadata + transcripts.\n")


if __name__ == "__main__":
    main()
