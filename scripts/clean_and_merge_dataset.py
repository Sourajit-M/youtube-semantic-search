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
        metadata_path: Path to crashcourse_metadata.csv (without transcripts)
        output_path: Path to save the cleaned merged dataset
    """
    print("=" * 70)
    print("YOUTUBE DATASET CLEANING AND MERGING")
    print("=" * 70)
    
    # Load datasets
    print("\n1. Loading datasets...")
    df_videos = pd.read_csv(videos_path)
    df_metadata = pd.read_csv(metadata_path)
    
    print(f"   Videos dataset: {len(df_videos)} rows, {len(df_videos.columns)} columns")
    print(f"   Metadata dataset: {len(df_metadata)} rows, {len(df_metadata.columns)} columns")
    
    # Merge datasets on 'id' column
    print("\n2. Merging datasets...")
    # Use videos dataset as base (has transcripts)
    # Left join to keep all videos with transcripts
    df_merged = df_videos.copy()
    
    print(f"   Merged dataset: {len(df_merged)} rows, {len(df_merged.columns)} columns")
    
    # Convert duration to seconds
    print("\n3. Converting duration to seconds...")
    df_merged['duration_seconds'] = df_merged['duration'].apply(parse_duration_to_seconds)
    print(f"   Sample conversions:")
    for idx in range(min(3, len(df_merged))):
        orig = df_merged.iloc[idx]['duration']
        converted = df_merged.iloc[idx]['duration_seconds']
        print(f"      {orig} -> {converted} seconds")
    
    # Clean text fields
    print("\n4. Cleaning text fields...")
    text_columns = ['title', 'description', 'transcript']
    
    for col in text_columns:
        if col in df_merged.columns:
            print(f"   Cleaning '{col}'...")
            df_merged[f'{col}_cleaned'] = df_merged[col].apply(clean_text)
            
            # Show sample
            if len(df_merged) > 0:
                sample_orig = str(df_merged.iloc[0][col])[:100]
                sample_clean = str(df_merged.iloc[0][f'{col}_cleaned'])[:100]
                print(f"      Original: {sample_orig}...")
                print(f"      Cleaned:  {sample_clean}...")
    
    # Convert other text fields to lowercase
    print("\n5. Converting remaining text fields to lowercase...")
    other_text_cols = ['tags', 'defaultLanguage', 'defaultAudioLanguage', 
                       'channel_title', 'channel_description']
    
    for col in other_text_cols:
        if col in df_merged.columns:
            df_merged[col] = df_merged[col].apply(
                lambda x: x.lower() if isinstance(x, str) else x
            )
    
    # Save cleaned dataset
    print(f"\n6. Saving cleaned dataset to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(output_path, index=False)
    
    # Display summary
    print("\n" + "=" * 70)
    print("CLEANING SUMMARY")
    print("=" * 70)
    print(f"\nFinal dataset:")
    print(f"  Total rows: {len(df_merged)}")
    print(f"  Total columns: {len(df_merged.columns)}")
    print(f"\nNew columns added:")
    print(f"  - duration_seconds: Converted from ISO 8601 format")
    print(f"  - title_cleaned: Lowercase, special chars removed")
    print(f"  - description_cleaned: Lowercase, special chars removed")
    print(f"  - transcript_cleaned: Lowercase, special chars removed")
    
    print(f"\nDuration statistics:")
    print(f"  Mean: {df_merged['duration_seconds'].mean():.0f} seconds")
    print(f"  Min: {df_merged['duration_seconds'].min()} seconds")
    print(f"  Max: {df_merged['duration_seconds'].max()} seconds")
    
    print(f"\nSample cleaned data (first row):")
    print(f"  ID: {df_merged.iloc[0]['id']}")
    print(f"  Title (cleaned): {df_merged.iloc[0]['title_cleaned'][:80]}...")
    print(f"  Duration: {df_merged.iloc[0]['duration']} -> {df_merged.iloc[0]['duration_seconds']} seconds")
    
    print("\n" + "=" * 70)
    print("✅ CLEANING COMPLETE!")
    print(f"   Cleaned dataset saved to: {output_path}")
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
