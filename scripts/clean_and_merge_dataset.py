"""
Data Cleaning and Merging Script for YouTube Semantic Search

This script:
1. Merges the video metadata and transcript datasets
2. Cleans text fields (title, transcript, description)
3. Removes special characters
4. Converts duration to seconds
5. Converts all text to lowercase
"""

import pandas as pd
import re
from pathlib import Path
import sys

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))


def parse_duration_to_seconds(duration_str):
    """
    Convert ISO 8601 duration format (PT#H#M#S) to total seconds.
    
    Examples:
        PT13M27S -> 807 seconds
        PT1H3M56S -> 3836 seconds
        PT2M41S -> 161 seconds
    
    Args:
        duration_str: ISO 8601 duration string
        
    Returns:
        int: Total duration in seconds
    """
    if pd.isna(duration_str) or not isinstance(duration_str, str):
        return 0
    
    # Remove 'PT' prefix
    duration_str = duration_str.replace('PT', '')
    
    hours = 0
    minutes = 0
    seconds = 0
    
    # Extract hours
    if 'H' in duration_str:
        hours_match = re.search(r'(\d+)H', duration_str)
        if hours_match:
            hours = int(hours_match.group(1))
    
    # Extract minutes
    if 'M' in duration_str:
        minutes_match = re.search(r'(\d+)M', duration_str)
        if minutes_match:
            minutes = int(minutes_match.group(1))
    
    # Extract seconds
    if 'S' in duration_str:
        seconds_match = re.search(r'(\d+)S', duration_str)
        if seconds_match:
            seconds = int(seconds_match.group(1))
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


def clean_text(text):
    """
    Clean text by removing special characters and converting to lowercase.
    
    Args:
        text: Input text string
        
    Returns:
        str: Cleaned text in lowercase
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters but keep spaces, alphanumeric, and basic punctuation
    # Keep: letters, numbers, spaces, periods, commas, apostrophes, hyphens
    text = re.sub(r'[^a-z0-9\s\.\,\'\-]', ' ', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def merge_and_clean_datasets(videos_path, metadata_path, output_path):
    """
    Merge and clean the YouTube datasets.
    
    Args:
        videos_path: Path to crashcourse_videos.csv (with transcripts)
        metadata_path: Path to crashcourse_metadata.csv (without transcripts) - optional
        output_path: Path to save the cleaned merged dataset
    """
    # Get relative paths for display
    try:
        videos_rel = videos_path.relative_to(Path.cwd())
        output_rel = output_path.relative_to(Path.cwd())
    except ValueError:
        videos_rel = videos_path.name
        output_rel = output_path.name
    
    print("=" * 70)
    print("YOUTUBE DATASET CLEANING AND MERGING")
    print("=" * 70)
    
    # Load datasets
    print("\n[1/6] Loading datasets...")
    df_videos = pd.read_csv(videos_path)
    print(f"   ✓ Loaded {len(df_videos)} videos with {len(df_videos.columns)} columns")
    
    # Check if metadata file exists (optional)
    if metadata_path.exists():
        df_metadata = pd.read_csv(metadata_path)
        print(f"   ✓ Loaded metadata: {len(df_metadata)} rows")
    else:
        print(f"   ℹ Metadata file not found (using videos dataset only)")
    
    # Use videos dataset as base
    print("\n[2/6] Preparing dataset...")
    df_merged = df_videos.copy()
    print(f"   ✓ Working with {len(df_merged)} rows")
    
    # Convert duration to seconds
    print("\n[3/6] Converting duration to seconds...")
    df_merged['duration_seconds'] = df_merged['duration'].apply(parse_duration_to_seconds)
    print(f"   ✓ Converted {len(df_merged)} duration values")
    
    # Clean text fields
    print("\n[4/6] Cleaning text fields...")
    text_columns = ['title', 'description', 'transcript']
    
    for col in text_columns:
        if col in df_merged.columns:
            df_merged[f'{col}_cleaned'] = df_merged[col].apply(clean_text)
            print(f"   ✓ Cleaned '{col}' column")
    
    # Convert other text fields to lowercase
    print("\n[5/6] Converting text to lowercase...")
    other_text_cols = ['tags', 'defaultLanguage', 'defaultAudioLanguage', 
                       'channel_title', 'channel_description']
    
    converted_count = 0
    for col in other_text_cols:
        if col in df_merged.columns:
            df_merged[col] = df_merged[col].apply(
                lambda x: x.lower() if isinstance(x, str) else x
            )
            converted_count += 1
    print(f"   ✓ Converted {converted_count} additional text columns")
    
    # Save cleaned dataset
    print(f"\n[6/6] Saving cleaned dataset...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(output_path, index=False)
    print(f"   ✓ Saved to: {output_rel}")
    
    # Display summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n📊 Dataset Statistics:")
    print(f"   • Total videos: {len(df_merged)}")
    print(f"   • Total columns: {len(df_merged.columns)}")
    
    print(f"\n🆕 New Columns:")
    print(f"   • duration_seconds (converted from ISO 8601)")
    print(f"   • title_cleaned (lowercase, special chars removed)")
    print(f"   • description_cleaned (lowercase, special chars removed)")
    print(f"   • transcript_cleaned (lowercase, special chars removed)")
    
    print(f"\n⏱️  Duration Statistics:")
    print(f"   • Average: {df_merged['duration_seconds'].mean():.0f}s ({df_merged['duration_seconds'].mean()/60:.1f} min)")
    print(f"   • Range: {df_merged['duration_seconds'].min()}s - {df_merged['duration_seconds'].max()}s")
    
    print("\n" + "=" * 70)
    print("✅ CLEANING COMPLETE!")
    print("=" * 70 + "\n")
    
    return df_merged


def main():
    """Main execution function."""
    # Define paths
    data_dir = ROOT_DIR / "data"
    videos_path = data_dir / "crashcourse_videos.csv"
    metadata_path = data_dir / "crashcourse_metadata.csv"
    output_path = data_dir / "crashcourse_cleaned.csv"
    
    # Run cleaning and merging
    df_cleaned = merge_and_clean_datasets(videos_path, metadata_path, output_path)
    
    return df_cleaned


if __name__ == "__main__":
    main()
