---
title: YouTube RAG Engine
emoji: ▶
colorFrom: red
colorTo: gray
sdk: docker
pinned: false
---

# 📺 YouTube RAG Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-LLM--Agnostic-blue)](https://github.com/BerriAI/litellm)
[![VectorDB](https://img.shields.io/badge/ChromaDB-Vector--Search-green)](https://www.trychroma.com/)

A production-grade Retrieval-Augmented Generation (RAG) system that lets you search and ask questions across any YouTube channel's transcript content.

🔗 **Live Demo:** [https://youtube-rag-engine.onrender.com/]
📖 **API Docs:** [https://huggingface.co/spaces/sourajitm19/youtube_rag/docs](https://huggingface.co/spaces/sourajitm19/youtube_rag/docs)

---

## ✨ Features

*   **Selective Ingestion:** Paste a single video URL for instant learning, or add an entire channel and pick exactly which videos to index.
*   **Grounded Answers:** Ask natural language questions and receive answers grounded in real video content with source citations.
*   **SaaS-Ready Architecture:** Clean, modular design ready for multi-user isolated workspaces.
*   **Hybrid Retrieval:** Uses RRF (Reciprocal Rank Fusion) to combine BM25 (exact term matching) and Vector Search (semantic similarity).
*   **Provider Agnostic:** Powered by LiteLLM to easily swap between providers like Groq and Gemini.
*   **Background Sync:** Background scheduler polls channels automatically for new content.

---

## 🏗️ Architecture

### High-Level Flow
1.  **Ingestion:** YouTube API → `yt-dlp` → `TranscriptChunker` → `FastEmbed` → `ChromaDB`.
2.  **Retrieval:** Hybrid Retriever combines BM25 and Vector search (ChromaDB) using RRF fusion.
3.  **Generation:** RAG pipeline sends retrieved chunks and prompts through LiteLLM (Groq primary, Gemini fallback).

---

## 🛠️ Tech Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **API** | FastAPI + Pydantic v2 | Async, auto-docs, and type-safety. |
| **LLM Gateway** | LiteLLM | Provider-agnostic with one-line switching. |
| **Vector DB** | ChromaDB | Persistent, local-first HNSW indexing. |
| **Keyword Search** | rank-bm25 | Provides exact term recall. |
| **Embeddings** | FastEmbed | CPU-only ONNX runtime using MiniLM-L6-v2. |
| **Metadata DB** | SQLite + SQLModel | Manages channels, videos, and job tracking. |
| **Package Mgr** | uv | 10-100x faster than pip with lock file support. |

---

## 🚀 Quickstart

### 1. Prerequisites
*   Python 3.11+
*   uv (`pip install uv`)
*   API keys: Groq, Gemini, YouTube Data API v3

### 2. Setup
```bash
git clone https://github.com/yourname/youtube-rag-engine
cd youtube-rag-engine

# Sync dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start server
uv run uvicorn app.api.main:app --reload --port 8000

# Start UI
uv run streamlit run main.py --server.port 8501
```

## 🕹️ Usage Examples

### Add a Single Video (Recommended)
Paste a direct URL to quickly learn from one video:
```bash
curl -X POST http://localhost:8000/channels \
  -H "Content-Type: application/json" \
  -d '{"channel_input": "https://www.youtube.com/watch?v=3JdpD3X2Md8"}'
```

### Add a Channel (Selective)
```bash
curl -X POST http://localhost:8000/channels \
  -H "Content-Type: application/json" \
  -d '{"channel_input": "@crashcourse", "max_videos": 5}'
```

### Ask a Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How was the Earth formed?"}'
```
## 📂 Project Structure
```
app/
├── api/          # FastAPI routes, Pydantic models
├── core/         # Chunker, embedder, retriever, LLM, RAG pipeline
├── db/           # ChromaDB handler, SQLite models
└── ingestion/    # YouTube API, transcript extraction, pipeline, scheduler
eval/             # Labelled questions + evaluation harness
tests/            # 27 pytest tests covering all core modules
```

## Key design decisions

**Why chunking over full-transcript embedding**  
Embedding entire transcripts dilutes meaning across topics. 300-token
chunks with 50-token overlap keep each embedding focused on one idea,
improving retrieval precision significantly.

**Why hybrid search over pure vector search**  
Vector search misses exact terms (a query for "CRISPR" may not retrieve
chunks that don't discuss gene editing semantically). BM25 catches exact
terms but misses meaning. RRF fusion covers both blind spots.

**Why LiteLLM**  
Provider lock-in is a real production risk. LiteLLM gives a single
`completion()` interface over 100+ providers. Switching from Groq to
Gemini requires changing one environment variable, not refactoring code.

**Why APScheduler over Celery**  
Celery requires a Redis broker — unnecessary operational complexity for
hourly polling at this scale. APScheduler runs in-process. The upgrade
path to Celery is clear if throughput demands it.
