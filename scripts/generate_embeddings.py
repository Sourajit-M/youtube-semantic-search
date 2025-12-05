"""
Embedding Generation Script for YouTube Semantic Search

This script:
1. Loads the cleaned dataset (crashcourse_final.csv)
2. Combines title and transcript columns
3. Generates embeddings using sentence-transformers
4. Saves embeddings back to the CSV file
"""

import os
import warnings

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import sys
from tqdm import tqdm
import json

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))


def combine_text(title, transcript, separator=" | "):
    """
    Combine title and transcript into a single text for embedding.
    
    Args:
        title: Video title (cleaned)
        transcript: Video transcript (cleaned)
        separator: String to separate title and transcript
        
    Returns:
        str: Combined text
    """
    # Handle missing values
    title = str(title) if pd.notna(title) else ""
    transcript = str(transcript) if pd.notna(transcript) else ""
    
    # Combine with separator
    combined = f"{title}{separator}{transcript}"
    
    return combined.strip()


def generate_embeddings(texts, model_name='all-MiniLM-L6-v2', batch_size=32, show_progress=True):
    """
    Generate embeddings for a list of texts using sentence-transformers.
    
    Args:
        texts: List of text strings to embed
        model_name: Name of the sentence-transformer model
        batch_size: Batch size for encoding
        show_progress: Whether to show progress bar
        
    Returns:
        np.ndarray: Array of embeddings (shape: [n_texts, embedding_dim])
    """
    print(f"\n[1/3] Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print(f"[2/3] Generating embeddings for {len(texts)} texts...")
    print(f"   • Batch size: {batch_size}")
    print(f"   • Embedding dimension: {model.get_sentence_embedding_dimension()}")
    
    # Generate embeddings with progress bar
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True
    )
    
    print(f"[3/3] ✓ Generated embeddings with shape: {embeddings.shape}")
    
    return embeddings


def embeddings_to_string(embeddings):
    """
    Convert numpy embeddings array to string format for CSV storage.
    
    Args:
        embeddings: numpy array of embeddings
        
    Returns:
        list: List of string representations
    """
    # Convert each embedding to a JSON string (more robust than comma-separated)
    return [json.dumps(emb.tolist()) for emb in embeddings]


def string_to_embeddings(embedding_strings):
    """
    Convert string representations back to numpy arrays.
    
    Args:
        embedding_strings: List of JSON string embeddings
        
    Returns:
        np.ndarray: Array of embeddings
    """
    return np.array([json.loads(s) for s in embedding_strings])


def save_embeddings_to_csv(df, output_path):
    """
    Save dataframe with embeddings to CSV.
    
    Args:
        df: DataFrame with embeddings column
        output_path: Path to save the CSV
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    # Get file size
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    
    print(f"\n✓ Saved dataset with embeddings to: {output_path.name}")
    print(f"   • File size: {file_size_mb:.2f} MB")


def main():
    """Main execution function."""
    print("=" * 70)
    print("YOUTUBE VIDEO EMBEDDING GENERATION")
    print("=" * 70)
    
    # Define paths
    data_dir = ROOT_DIR / "data"
    input_path = data_dir / "crashcourse_final.csv"
    output_path = data_dir / "crashcourse_final.csv"  # Overwrite the same file
    
    # Load dataset
    print(f"\n📂 Loading dataset from: {input_path.name}")
    df = pd.read_csv(input_path)
    print(f"   ✓ Loaded {len(df)} videos with {len(df.columns)} columns")
    
    # Verify required columns exist
    required_cols = ['title', 'transcript']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    print(f"\n🔗 Combining title and transcript columns...")
    # Combine text
    combined_texts = [
        combine_text(row['title'], row['transcript']) 
        for _, row in df.iterrows()
    ]
    
    # Show sample
    print(f"   ✓ Combined {len(combined_texts)} texts")
    print(f"\n   Sample combined text (first 200 chars):")
    print(f"   '{combined_texts[0][:200]}...'")
    
    # Generate embeddings
    print(f"\n🤖 Generating embeddings...")
    embeddings = generate_embeddings(
        combined_texts,
        model_name='all-MiniLM-L6-v2',
        batch_size=32,
        show_progress=True
    )
    
    # Convert embeddings to string format for CSV
    print(f"\n💾 Preparing embeddings for CSV storage...")
    embedding_strings = embeddings_to_string(embeddings)
    
    # Add embeddings column to dataframe
    df['embeddings'] = embedding_strings
    
    print(f"   ✓ Added 'embeddings' column to dataframe")
    
    # Save to CSV
    print(f"\n📝 Saving updated dataset...")
    save_embeddings_to_csv(df, output_path)
    
    # Display summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n📊 Embedding Statistics:")
    print(f"   • Total videos: {len(df)}")
    print(f"   • Embedding dimension: {embeddings.shape[1]}")
    print(f"   • Model used: all-MiniLM-L6-v2")
    print(f"   • Storage format: JSON strings in CSV")
    
    print(f"\n✅ Dataset columns ({len(df.columns)} total):")
    cols_per_line = 3
    for i in range(0, len(df.columns), cols_per_line):
        cols_batch = df.columns[i:i+cols_per_line]
        print(f"   • {', '.join(cols_batch)}")
    
    print("\n" + "=" * 70)
    print("✅ EMBEDDING GENERATION COMPLETE!")
    print("=" * 70)
    
    # Verification example
    print(f"\n💡 To load and use embeddings in Python:")
    print(f"   import pandas as pd")
    print(f"   import numpy as np")
    print(f"   import json")
    print(f"   ")
    print(f"   df = pd.read_csv('data/crashcourse_final.csv')")
    print(f"   embeddings = np.array([json.loads(e) for e in df['embeddings']])")
    print(f"   print(embeddings.shape)  # Should be ({len(df)}, {embeddings.shape[1]})")
    print()
    
    return df


if __name__ == "__main__":
    main()
