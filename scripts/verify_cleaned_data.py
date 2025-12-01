"""
Verification script to check the cleaned dataset
"""

import pandas as pd
from pathlib import Path

# Load the cleaned dataset
data_dir = Path(__file__).resolve().parents[1] / "data"
cleaned_path = data_dir / "crashcourse_cleaned.csv"

df = pd.read_csv(cleaned_path)

print("=" * 70)
print("CLEANED DATASET VERIFICATION")
print("=" * 70)

print(f"\nDataset shape: {df.shape[0]} rows × {df.shape[1]} columns")

print("\nColumn names:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print("\n" + "=" * 70)
print("SAMPLE DATA (First Row)")
print("=" * 70)

print(f"\nVideo ID: {df.iloc[0]['id']}")
print(f"\nOriginal Title:\n  {df.iloc[0]['title'][:100]}...")
print(f"\nCleaned Title:\n  {df.iloc[0]['title_cleaned'][:100]}...")

print(f"\nOriginal Duration: {df.iloc[0]['duration']}")
print(f"Duration in Seconds: {df.iloc[0]['duration_seconds']}")

print(f"\nOriginal Description (first 150 chars):\n  {str(df.iloc[0]['description'])[:150]}...")
print(f"\nCleaned Description (first 150 chars):\n  {df.iloc[0]['description_cleaned'][:150]}...")

print(f"\nOriginal Transcript (first 200 chars):\n  {str(df.iloc[0]['transcript'])[:200]}...")
print(f"\nCleaned Transcript (first 200 chars):\n  {df.iloc[0]['transcript_cleaned'][:200]}...")

print("\n" + "=" * 70)
print("DURATION STATISTICS")
print("=" * 70)
print(f"\nMean duration: {df['duration_seconds'].mean():.2f} seconds ({df['duration_seconds'].mean()/60:.2f} minutes)")
print(f"Median duration: {df['duration_seconds'].median():.2f} seconds ({df['duration_seconds'].median()/60:.2f} minutes)")
print(f"Min duration: {df['duration_seconds'].min()} seconds")
print(f"Max duration: {df['duration_seconds'].max()} seconds ({df['duration_seconds'].max()/60:.2f} minutes)")

print("\n" + "=" * 70)
print("TEXT CLEANING VERIFICATION")
print("=" * 70)

# Check if text is lowercase
sample_title = df.iloc[0]['title_cleaned']
sample_desc = df.iloc[0]['description_cleaned']
sample_trans = df.iloc[0]['transcript_cleaned']

print(f"\nTitle is lowercase: {sample_title == sample_title.lower()}")
print(f"Description is lowercase: {sample_desc == sample_desc.lower()}")
print(f"Transcript is lowercase: {sample_trans == sample_trans.lower()}")

# Check for special characters (should be minimal)
import re
special_chars_title = len(re.findall(r'[^a-z0-9\s\.\,\'\-]', sample_title))
special_chars_desc = len(re.findall(r'[^a-z0-9\s\.\,\'\-]', sample_desc))

print(f"\nSpecial characters in cleaned title: {special_chars_title}")
print(f"Special characters in cleaned description: {special_chars_desc}")

print("\n" + "=" * 70)
print("✅ VERIFICATION COMPLETE!")
print("=" * 70)
