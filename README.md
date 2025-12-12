# 🔍 YouTube Semantic Search Engine

> **Find YouTube videos using natural language** - No more keyword hunting! Just ask what you're looking for, and let AI understand what you mean.

Hey there! 👋 Welcome to a semantic search engine that actually *understands* what you're asking for. Instead of just matching keywords, this system gets the meaning behind your question and finds the most relevant videos - even if they use completely different words.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Database-orange.svg)
![Status](https://img.shields.io/badge/status-Active-success.svg)

---

## 🎯 What's This All About?

Imagine you're searching for "learning algorithms" but the video title says "DSA tutorial" or "data structures explained". Traditional search might miss it, but this system won't! 

**Here's the magic:** We use AI language models to understand the *meaning* of both your query and all the video content (titles, descriptions, transcripts). Then we find what matches best semantically - not just by keywords.

### ✨ What Makes This Cool?

- 🧠 **Smart Understanding** - Uses transformer models to grasp what you actually mean
- 📝 **Full Content Search** - Searches through titles, descriptions, AND complete transcripts
- ⚡ **Lightning Fast** - ChromaDB vector database for instant results
- 🎯 **Relevant Results** - Returns the top matches that actually answer your question
- 🗄️ **Scalable** - Built with ChromaDB for efficient storage and retrieval

---

## 📚 Table of Contents

- [How It Works](#-how-it-works)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Usage Guide](#-usage-guide)
- [Project Structure](#-project-structure)
- [What I've Built So Far](#-what-ive-built-so-far)
- [Example Searches](#-example-searches)
- [What's Next](#-whats-next)

---

## 🧠 How It Works

Let me break down the magic in simple terms:

### The Pipeline

```
📺 YouTube Videos
    ↓
🔍 Fetch metadata & transcripts  
    ↓
🧹 Clean & process text
    ↓
🤖 Generate AI embeddings (384-dimensional vectors)
    ↓
💾 Store in ChromaDB vector database
    ↓
❓ Your search query
    ↓
🎯 Find most similar videos
    ↓
✅ Get your results!
```

### What Happens Behind the Scenes?

1. **Data Collection** - Grab videos from a YouTube channel (currently using CrashCourse)
2. **Transcript Extraction** - Pull the full text transcript for each video
3. **Text Cleaning** - Normalize everything: lowercase, remove weird characters, etc.
4. **AI Magic** - Convert text into 384-dimensional vectors using `all-MiniLM-L6-v2` model
5. **Vector Storage** - Save everything in ChromaDB for fast similarity search
6. **Search Time** - When you ask a question, we convert it to a vector and find the closest matches!

The beauty is in **semantic similarity** - similar meanings cluster together in vector space, even with different words.

---

## 🛠️ Tech Stack

Here's what powers this project:

### Core Technologies
- **Python 3.8+** - The language that brings it all together
- **ChromaDB** - Vector database for efficient similarity search
- **Sentence Transformers** - AI models for text embeddings (`all-MiniLM-L6-v2`)
- **pandas** - Data wrangling and processing
- **scikit-learn** - Distance metrics and similarity calculations

### APIs & Services
- **YouTube Data API v3** - Fetching video metadata
- **YouTube Transcript API** - Extracting video transcripts
- **python-dotenv** - Managing API keys securely

### Future Additions
- **Gradio** - Web interface (coming soon!)
- **PyTorch** - Deep learning backend

---

## 🚀 Getting Started

### What You'll Need

- Python 3.8 or higher
- A Google Cloud account (free tier works!)
- About 2GB of free disk space
- 10-15 minutes of your time

### Installation Steps

**1. Clone this repository**
```bash
git clone https://github.com/yourusername/youtube-semantic-search.git
cd youtube-semantic-search
```

**2. Set up a virtual environment** (always a good idea!)
```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On Mac/Linux
```

**3. Install all dependencies**
```bash
pip install -r requirements.txt
```

**4. Get your YouTube API key**

Don't worry, it's easier than it sounds:
- Head to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project (name it whatever you like)
- Enable "YouTube Data API v3"
- Create an API key
- Copy that key!

**5. Set up your environment**

Create a `.env` file in the project root:
```bash
YOUTUBE_API_KEY=your_actual_api_key_here
```

That's it! You're ready to roll. 🎉

---

## 📖 Usage Guide

### Running the Complete Pipeline

Here's how to go from zero to searchable database:

**Step 1: Fetch YouTube videos**
```bash
python scripts/extract_transcript.py
```
This grabs video metadata and transcripts from the YouTube channel.

**Step 2: Clean the data**
```bash
python scripts/clean_and_merge_dataset.py
```
Normalizes text, removes junk, and prepares data for embedding.

**Step 3: Generate embeddings**
```bash
python scripts/generate_embeddings.py
```
Converts all video content into AI-powered vector embeddings.

**Step 4: Store in vector database**
```bash
python scripts/migrate_to_vectordb.py
```
Loads everything into ChromaDB for fast semantic search.

**Step 5: Search!**
```bash
python scripts/semantic_search.py
```
Start searching with natural language queries!

### Quick Search Example

```python
from scripts.semantic_search import search_videos

# Just ask naturally!
results = search_videos("explain quantum physics simply", top_k=5)

for video in results:
    print(f"📺 {video['title']}")
    print(f"   Similarity: {video['similarity']:.2%}")
    print(f"   Link: {video['url']}\n")
```

---

## 📁 Project Structure

Here's how everything is organized:

```
youtube-semantic-search/
│
├── .env                          # Your API keys (don't commit this!)
├── config.py                     # Project configuration
├── requirements.txt              # All dependencies
│
├── data/                         # All data files
│   ├── crashcourse_videos.csv   # Raw video metadata
│   ├── crashcourse_final.csv    # Processed data with transcripts
│   ├── failed_transcripts.txt   # Videos that failed
│   └── vectordb/                # ChromaDB storage
│
└── scripts/                      # The magic happens here
    ├── extract_transcript.py        # Fetches videos & transcripts
    ├── clean_and_merge_dataset.py   # Data cleaning
    ├── generate_embeddings.py       # Creates AI embeddings
    ├── migrate_to_vectordb.py       # Loads into ChromaDB
    ├── semantic_search.py           # Search interface
    ├── db_handler.py                # ChromaDB operations
    └── test_vectordb.py             # Tests & validation
```

**Quick Breakdown:**
- `config.py` - Central configuration (model name, API keys, paths)
- `scripts/` - All executable scripts for the pipeline
- `data/` - Where all the data lives (CSVs, vector database)
- `.env` - Your secret API keys (create this manually!)

---

## ✅ What I've Built So Far

### ✨ Milestone 1: Data Collection ✅ 
Successfully extracted video data from CrashCourse YouTube channel including:
- Video titles, descriptions, IDs
- Publish dates and metadata
- **Result:** ~1,000+ videos cataloged

### ✨ Milestone 2: Transcript Processing ✅
- Extracted full transcripts using YouTube Transcript API
- Handled failed extractions gracefully
- Cleaned and normalized all text data
- **Result:** High-quality dataset with full video content

### ✨ Milestone 3: Embeddings & Vector DB ✅
- Implemented `all-MiniLM-L6-v2` for 384-dim embeddings
- Integrated ChromaDB vector database
- Created migration scripts for efficient storage
- **Result:** Fast, scalable semantic search ready!

### 🔄 Milestone 4: Search Interface (In Progress)
- Built semantic search functionality
- Testing query performance
- Planning Gradio web interface
- **Next:** Deploy user-friendly web UI

---

## 🔍 Example Searches

Here's what you can do with this system:

### Example 1: Learning Topics
```
🔎 Query: "introduction to biology for beginners"

📺 Result: "Biology - It's in Your Blood: Crash Course Biology #2"
   Similarity: 92.4%
   
📺 Result: "Introduction to Cells: The Grand Cell Tour"  
   Similarity: 89.7%
```

### Example 2: Specific Concepts
```
🔎 Query: "how does photosynthesis work"

📺 Result: "Photosynthesis: Crash Course Biology #8"
   Similarity: 95.2%
   
📺 Result: "Plant Cells: Crash Course Biology #6"
   Similarity: 84.6%
```

### Example 3: Historical Events
```
🔎 Query: "world war 2 timeline and events"

📺 Result: "World War II: Crash Course World History #38"
   Similarity: 91.8%
```

Notice how it finds relevant content even without exact keyword matches!

---

## 🔮 What's Next?

Here are the exciting enhancements I'm planning:

### Short Term
- [ ] 🖥️ **Web Interface** - Beautiful Gradio UI for easy searching
- [ ] 📊 **Model Comparison** - Test different embedding models
- [ ] 🎯 **Result Ranking** - Improve relevance scoring

### Medium Term  
- [ ] 🔍 **Timestamp Search** - Find specific moments in videos
- [ ] 🏷️ **Filters** - Search by date, duration, channel
- [ ] 📈 **Analytics** - Track popular queries and performance

### Long Term
- [ ] 🌐 **Multi-Channel** - Support searching across multiple channels
- [ ] 🌍 **Multi-Language** - Support non-English content
- [ ] ☁️ **Cloud Deployment** - Deploy on Hugging Face Spaces or AWS
- [ ] 🤝 **User Feedback** - Learn from user interactions to improve results
- [ ] ⚡ **FAISS Integration** - Even faster search at massive scale

---

## 🤝 Want to Contribute?

I'd love your help making this better! Here's how:

1. **Fork** this repository
2. **Create** a feature branch: `git checkout -b cool-new-feature`
3. **Commit** your changes: `git commit -m 'Add some cool feature'`
4. **Push** to your branch: `git push origin cool-new-feature`
5. **Open** a Pull Request

### Ideas for Contributions
- Add more embedding models to compare
- Build a better web interface
- Improve text preprocessing
- Add unit tests
- Optimize search performance
- Create visualization tools

---

## 📝 Notes & Learnings

### Why ChromaDB?
I chose ChromaDB because it's:
- **Simple** - Easy to set up and use
- **Fast** - Optimized for similarity search
- **Local** - No external services needed
- **Scalable** - Can handle millions of vectors

### Model Choice: all-MiniLM-L6-v2
This model strikes a great balance:
- ✅ Fast inference (~12ms per query)
- ✅ Good accuracy for English text
- ✅ Smaller size (384 dimensions)
- ✅ Perfect for educational content

### Challenges Faced
1. **API Rate Limits** - YouTube API has quotas (solved with smart batching)
2. **Missing Transcripts** - Some videos don't have them (logged and skipped)
3. **Memory Management** - Large embeddings (solved with ChromaDB)

---

## 🙏 Acknowledgments

Big thanks to:
- **CrashCourse** - Amazing educational content
- **Sentence-BERT** - Powerful embedding models from [SBERT.net](https://www.sbert.net/)
- **ChromaDB** - Fantastic vector database
- **Hugging Face** - Transformer models and community
- **YouTube** - API access to video data

---

## 📄 License

This project is open source under the MIT License. Feel free to use it, modify it, and learn from it!

---

## 📧 Let's Connect!

Found this useful? Have questions? Want to collaborate?

- **GitHub**: [@yourusername](https://github.com/yourusername)
- **Twitter**: [@yourhandle](https://twitter.com/yourhandle)
- **Email**: your.email@example.com

---

⭐ **If this project helped you, consider giving it a star!** ⭐

Built with ❤️ and lots of ☕ as part of my machine learning journey.

Happy searching! 🚀
