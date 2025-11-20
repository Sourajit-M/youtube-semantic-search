# 🔍 QueryTube: YouTube Semantic Search Engine

A semantic search engine that allows users to find YouTube videos using natural language queries. Instead of simple keyword matching, this system understands the *meaning* of your search and returns the most relevant videos from a YouTube channel.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-In%20Development-yellow.svg)

## 🎯 Project Overview

**QueryTube** uses state-of-the-art transformer models to create embeddings of video titles and transcripts, enabling intelligent semantic search. When you ask "how to learn data structures", it finds relevant videos even if they use different terminology like "DSA tutorials" or "algorithms explained".

### Key Features
- 🤖 Semantic understanding of natural language queries
- 📊 Processes video titles, descriptions, and full transcripts
- 🎯 Returns top-5 most relevant videos based on meaning, not just keywords
- 🖥️ Interactive web interface built with Gradio
- ⚡ Fast similarity search using optimized distance metrics

## 📚 Table of Contents
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Project Milestones](#project-milestones)
- [How It Works](#how-it-works)
- [Results](#results)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

```
┌─────────────┐
│ YouTube API │
└──────┬──────┘
       │
       ▼
┌────────────────┐
│ Data Extractor │ → Video Metadata (Title, Date, ID)
└────────┬───────┘
         │
         ▼
┌─────────────────┐
│ Transcript API  │ → Full Video Transcripts
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│ Text Cleaning    │ → Normalized Text
└────────┬─────────┘
         │
         ▼
┌────────────────────┐
│ SentenceTransformer│ → 768-dim Embeddings
└────────┬───────────┘
         │
         ▼
┌──────────────────┐
│ Similarity Search│ → Top-5 Results
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│ Gradio UI    │ → User Interface
└──────────────┘
```

## 🛠️ Tech Stack

### Core Libraries
- **Python 3.8+** - Programming language
- **google-api-python-client** - YouTube Data API integration
- **youtube-transcript-api** - Transcript extraction
- **sentence-transformers** - Text embedding models
- **pandas/polars** - Data manipulation
- **scikit-learn** - Distance metrics and similarity calculations
- **gradio** - Web interface

### Machine Learning
- **Sentence-BERT** - Transformer-based embeddings
- **Cosine Similarity** - Semantic similarity measurement
- **Vector Search** - Efficient retrieval

## 📁 Project Structure

```
youtube-semantic-search/
│
├── data/
│   ├── raw/
│   │   └── apna_college_videos.csv
│   ├── processed/
│   │   └── videos_with_transcripts.csv
│   └── embeddings/
│       └── video_embeddings.parquet
│
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_transcript_extraction.ipynb
│   ├── 03_model_evaluation.ipynb
│   └── 04_search_optimization.ipynb
│
├── src/
│   ├── __init__.py
│   ├── data_extraction.py
│   ├── transcript_handler.py
│   ├── text_preprocessing.py
│   ├── embedding_generator.py
│   ├── search_engine.py
│   └── utils.py
│
├── app/
│   └── gradio_app.py
│
├── tests/
│   └── test_search.py
│
├── evaluation/
│   ├── queries.txt
│   └── model_comparison.csv
│
├── requirements.txt
├── config.py
├── README.md
└── .gitignore
```

## ⚙️ Installation

### Prerequisites
- Python 3.8 or higher
- Google Cloud account (for YouTube API)
- 2GB free disk space

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/youtube-semantic-search.git
   cd youtube-semantic-search
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up YouTube API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable YouTube Data API v3
   - Create credentials (API Key)
   - Copy your API key

5. **Configure environment**
   ```bash
   # Create config.py
   echo "YOUTUBE_API_KEY = 'your_api_key_here'" > config.py
   ```

6. **Create data directories**
   ```bash
   mkdir -p data/raw data/processed data/embeddings
   ```

## 🚀 Usage

### Step 1: Extract Video Data
```bash
python src/data_extraction.py
```

### Step 2: Get Transcripts
```bash
python src/transcript_handler.py
```

### Step 3: Generate Embeddings
```bash
python src/embedding_generator.py
```

### Step 4: Run Search Engine
```bash
python src/search_engine.py --query "how to learn python"
```

### Step 5: Launch Web Interface
```bash
python app/gradio_app.py
```
Then open `http://localhost:7860` in your browser.

## 🎓 Project Milestones

### ✅ Milestone 1: Data Collection (Weeks 1-2)
- Set up YouTube API authentication
- Extract video metadata from channel
- Perform exploratory data analysis
- **Deliverable**: CSV with 100-350 videos

### ✅ Milestone 2: Transcript Extraction (Weeks 3-4)
- Extract transcripts using YouTube Transcript API
- Clean and normalize text data
- Create evaluation query dataset
- **Deliverable**: Dataset with titles, dates, and transcripts

### 🔄 Milestone 3: Model Evaluation (Weeks 5-6)
- Test 3+ SentenceTransformer models
- Compare distance metrics (Euclidean, Manhattan, Cosine)
- Evaluate model performance on test queries
- **Deliverable**: Model comparison report

### ⏳ Milestone 4: Deployment (Weeks 7-8)
- Implement optimized search function
- Build Gradio web interface
- Create final documentation
- **Deliverable**: Production-ready search engine

## 🧠 How It Works

### 1. **Data Collection**
Videos are fetched from YouTube API with metadata including title, description, and publish date.

### 2. **Transcript Extraction**
Auto-generated or manual transcripts are retrieved for each video, providing the full content for semantic analysis.

### 3. **Text Embedding**
Both queries and video content are converted to 768-dimensional vectors using SentenceTransformer models like `all-MiniLM-L6-v2`.

### 4. **Similarity Search**
When a user enters a query:
```python
query_embedding = model.encode(user_query)
similarities = cosine_similarity(query_embedding, video_embeddings)
top_5_indices = similarities.argsort()[-5:][::-1]
```

### 5. **Result Ranking**
Videos are ranked by semantic similarity score, with the top-5 most relevant results returned.

## 📊 Results

### Model Performance (Example)

| Model | Avg Rank | Top-1 Accuracy | Top-3 Recall | Inference Time |
|-------|----------|----------------|--------------|----------------|
| all-MiniLM-L6-v2 | 2.3 | 65% | 85% | 12ms |
| all-mpnet-base-v2 | 1.8 | 72% | 91% | 28ms |
| paraphrase-multilingual | 2.1 | 68% | 87% | 35ms |

### Example Queries
```
Query: "learn data structures in java"
Top Result: "Complete DSA Course in Java - Arrays & LinkedLists"
Similarity: 0.89

Query: "web development tutorial for beginners"
Top Result: "HTML CSS JavaScript - Complete Web Dev Course"
Similarity: 0.91
```

## 🔮 Future Enhancements

- [ ] Add multi-language support
- [ ] Implement video timestamp search (find exact moments)
- [ ] Add filtering by video duration, date, views
- [ ] Integrate FAISS for faster vector search at scale
- [ ] Add query expansion and synonym handling
- [ ] Deploy on cloud (Hugging Face Spaces/AWS)
- [ ] Add user feedback loop for improving results
- [ ] Support multiple YouTube channels

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Apna College** - YouTube channel used for this implementation
- **Sentence-BERT** - Embedding models from [SBERT.net](https://www.sbert.net/)
- **Hugging Face** - Transformer models and libraries
- **YouTube API** - Data source

## 📧 Contact

Your Name - [@yourhandle](https://twitter.com/yourhandle)

Project Link: [https://github.com/yourusername/youtube-semantic-search](https://github.com/yourusername/youtube-semantic-search)

---

⭐ If you found this project helpful, please give it a star!

**Built with ❤️ as part of an ML internship project**
