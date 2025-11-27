import pandas as pd
import time
import re
import requests


SEARCHAPI_KEY = 'THk5exssBrgHTYH5Wa25VYNR'
INPUT_FILE = 'data/crashcourse_videos.csv'
OUTPUT_FILE = 'data/crashcourse_with_transcripts.csv'
FAILED_LOG = 'data/failed_transcripts.txt'


def get_transcript_searchapi(video_id, api_key):
    """
    Fetch transcript using SearchAPI.
    
    Args:
        video_id: YouTube video ID
        api_key: SearchAPI key
    
    Returns:
        tuple: (success: bool, transcript: str or error: str)
    """
    url = "https://www.searchapi.io/api/v1/search"
    
    params = {
        "engine": "youtube_transcripts",
        "video_id": video_id,
        "api_key": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if transcript exists
            if 'transcripts' in data and len(data['transcripts']) > 0:
                # Combine all transcript segments
                transcript_text = ' '.join([
                    segment.get('text', '') 
                    for segment in data['transcripts']
                ])
                return True, transcript_text
            else:
                return False, "No transcript available"
        
        elif response.status_code == 401:
            return False, "Invalid API key"
        
        elif response.status_code == 429:
            return False, "Rate limit exceeded"
        
        else:
            return False, f"HTTP {response.status_code}"
    
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


def extract_all_transcripts_searchapi(df, api_key, delay=0.5):
    """
    Extract transcripts for all videos using SearchAPI with detailed progress.
    
    Args:
        df: DataFrame with video_id or id column
        api_key: SearchAPI key
        delay: Delay between requests (seconds)
    
    Returns:
        DataFrame with 'transcript' column added
    """

    print("EXTRACTING TRANSCRIPTS VIA SEARCHAPI")
    
    transcripts = []
    failed_videos = []
    
    video_id_col = 'id' if 'id' in df.columns else 'video_id'
    total = len(df)
    
    print(f"Total videos to process: {total}\n")
    
    for idx, row in df.iterrows():
        video_id = row[video_id_col]
        title = str(row['title'])[:50]  # Truncate for display
        
        # Progress with title
        print(f"[{idx + 1}/{total}] {title}...", end=" ")
        
        success, result = get_transcript_searchapi(video_id, api_key)
        
        if success:
            transcripts.append(result)
            word_count = len(result.split())
            print(f"✓ ({word_count} words)")
        else:
            transcripts.append(None)
            failed_videos.append({
                'video_id': video_id,
                'title': row['title'],
                'error': result
            })
            print(f"✗ Failed ({result})")
        
        # Respect rate limits
        time.sleep(delay)
    
    # Add column
    df['transcript'] = transcripts
    
    # Log failures
    if failed_videos:
        with open(FAILED_LOG, 'w', encoding='utf-8') as f:
            f.write(f"FAILED TRANSCRIPT EXTRACTIONS\n")
            f.write(f"Total Failed: {len(failed_videos)}\n")
            f.write("="*60 + "\n\n")
            for i, video in enumerate(failed_videos, 1):
                f.write(f"{i}. Video ID: {video['video_id']}\n")
                f.write(f"   Title: {video['title']}\n")
                f.write(f"   Error: {video['error']}\n\n")
        print(f"\n⚠ Failed extractions logged to: {FAILED_LOG}")
    
    success_count = df['transcript'].notna().sum()
    failed_count = len(failed_videos)
    
    print(f"EXTRACTION SUMMARY")
    print(f"Successfully extracted: {success_count}/{total} transcripts")
    print(f"Failed: {failed_count} videos")
    print(f"Success rate: {(success_count/total*100):.1f}%")
    
    return df


def clean_text(text):
    """Clean and normalize text."""
    if pd.isna(text) or text is None or text == "":
        return ""
    
    text = str(text)
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?\-\'"]', ' ', text)
    
    # Remove multiple punctuation
    text = re.sub(r'([.,!?])\1+', r'\1', text)
    
    # Lowercase
    text = text.lower()
    
    return text.strip()

def clean_and_analyze(df):
    """Clean text and add analysis columns."""
    
    print("CLEANING TEXT DATA")
    
    # Clean titles
    print("Cleaning titles...")
    df['title_cleaned'] = df['title'].apply(clean_text)
    
    # Clean transcripts
    print("Cleaning transcripts...")
    df['transcript_cleaned'] = df['transcript'].apply(clean_text)
    
    # Calculate lengths
    df['transcript_length'] = df['transcript_cleaned'].apply(lambda x: len(x) if x else 0)
    df['transcript_word_count'] = df['transcript_cleaned'].apply(
        lambda x: len(x.split()) if x else 0
    )
    
    # Statistics
    valid = df[df['transcript'].notna()]
    
    if len(valid) > 0:
        print(f"\n✓ Cleaning complete!")
        print(f"\nTranscript Statistics:")
        print(f"  Videos with transcripts: {len(valid)}")
        print(f"  Avg length: {valid['transcript_length'].mean():.0f} characters")
        print(f"  Avg word count: {valid['transcript_word_count'].mean():.0f} words")
        print(f"  Shortest: {valid['transcript_length'].min()} chars")
        print(f"  Longest: {valid['transcript_length'].max()} chars")
    else:
        print("\n⚠ No valid transcripts found!")
    
    return df


if __name__ == "__main__":
    print("TRANSCRIPT EXTRACTION - CRASHCOURSE (SearchAPI)")
    
    # Verify API key
    if SEARCHAPI_KEY == 'YOUR_SEARCHAPI_KEY_HERE':
        print("ERROR: Please set your SearchAPI key!")
        print("\n1. Sign up at: https://www.searchapi.io/")
        print("2. Get your API key from dashboard")
        print("3. Replace SEARCHAPI_KEY in this script\n")
        raise SystemExit(1)
    
    # Load data
    print("Loading video metadata...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"ERROR: File not found: {INPUT_FILE}")
        print("\nMake sure you have:")
        print("  1. Run the CrashCourse extraction script")
        print("  2. File exists at: data/crashcourse_videos.csv")
        raise SystemExit(1)
    
    print(f"✓ Loaded {len(df)} videos\n")
    
    if len(df) < 50:
        print(f"WARNING: Only {len(df)} videos found!")
        print("Expected 250-350 videos for this project.")
        print("\nPossible issues:")
        print("  1. API key might be wrong (in your video scraping step)")
        print("  2. Extraction script stopped early")
        print("  3. API quota exceeded")
        print("\nContinuing with available videos...\n")
        time.sleep(2)
    
    df = extract_all_transcripts_searchapi(df, SEARCHAPI_KEY, delay=0.5)
    
    df = clean_and_analyze(df)
    
    # Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✓ Complete dataset saved to: {OUTPUT_FILE}")
    
    # Show sample
    valid_df = df[df['transcript'].notna()]
    if len(valid_df) > 0:
        print("SAMPLE VIDEO WITH TRANSCRIPT")
        sample = valid_df.iloc[0]
        print(f"\nTitle: {sample['title']}")
        if 'viewCount' in sample:
            try:
                print(f"Views: {int(sample['viewCount']):,}")
            except Exception:
                print(f"Views: {sample['viewCount']}")
        print(f"Transcript words: {sample['transcript_word_count']}")
        print(f"Preview: {sample['transcript_cleaned'][:200]}...")
        
        #stats
        print("FINAL DATASET STATISTICS")
        print(f"Total videos: {len(df)}")
        print(f"Videos with transcripts: {len(valid_df)}")
        print(f"Ready for semantic search: {'✓ YES' if len(valid_df) >= 100 else 'Need more videos'}")
    else:
        print("⚠ CRITICAL: NO TRANSCRIPTS EXTRACTED (SearchAPI)")
        print("\nThis shouldn't happen for most CrashCourse videos!")
        print("Please check:")
        print("  1. Are the video IDs correct in the CSV?")
        print("  2. Is your SearchAPI key valid and has quota?")
        print("  3. Try a single video with get_transcript_searchapi() for debugging")
    
    print("SCRIPT COMPLETE!")
