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

*   **Two-Stage Retrieval (Cross-Encoder Reranking):** Fetches top-20 candidates from hybrid search (BM25 + Vector + RRF) and scores them jointly using a Cross-Encoder to return the top-5 most relevant results.
*   **Enforced Structured Citations:** Zero-hallucination citation pipeline. The LLM output is forced to a validated JSON structure, and any cited video ID not present in retrieved chunks is programmatically rejected.
*   **AI-Selected Quotes Panel:** Displays direct citations with inline transcript quote blocks and interactive "Jump to timestamp" player links.
*   **Normalized Relevance Badges:** Translates cryptic raw RRF scores into intuitive, color-coded relevance percentages (e.g. `Relevance 94%`).
*   **Modern React UI Dashboard:** Features auto-scrolling queries, content-shaped skeleton loaders, safe client-side Markdown formatting, and detailed pipeline error/retry controls.
*   **Selective Ingestion:** Paste a single video URL for instant learning, or add an entire channel and pick exactly which videos to index.
*   **CI-Gated Evaluation Pipeline:** Automatically runs a 20-question multi-channel evaluation harness on every Pull Request, blocking merge if retrieval hit rate falls below 80%.
*   **Hybrid Retrieval:** Uses RRF (Reciprocal Rank Fusion) to combine BM25 (exact term matching) and Vector Search (semantic similarity).
*   **Provider Agnostic:** Powered by LiteLLM to easily swap between providers like Groq and Gemini.
*   **Background Sync:** Background scheduler polls channels automatically for new content.

---

## 🏗️ Architecture

### High-Level Flow
1.  **Ingestion:** YouTube API → `yt-dlp` → `TranscriptChunker` → `FastEmbed` → `ChromaDB` & SQLite FTS5.
2.  **Retrieval (Two-Stage):** 
    *   *First-Stage:* Retrieve candidate chunks using BM25 (SQLite FTS5) and Vector search (ChromaDB), fused together via Reciprocal Rank Fusion (RRF) to get the top-20 candidates.
    *   *Second-Stage:* Rerank candidates using a Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) scoring query-chunk pairs jointly, returning the top-5.
3.  **Generation:** RAG pipeline queries LiteLLM in JSON mode (`response_format={"type": "json_object"}`), validates returned citations, strips any hallucinated citations, and yields the final grounded response.

---

## 🛠️ Tech Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **API** | FastAPI + Pydantic v2 | Async, auto-docs, and type-safety. |
| **LLM Gateway** | LiteLLM | Provider-agnostic with one-line switching. |
| **Vector DB** | ChromaDB | Persistent, local-first HNSW indexing. |
| **Reranker** | sentence-transformers | Cross-Encoder `ms-marco-MiniLM-L-6-v2` for precise semantic relevance. |
| **Keyword Search** | SQLite FTS5 | Database-level exact term recall (replaces pickling). |
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
cd frontend
npm run dev
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
├── api/          # FastAPI routes, Pydantic models (AskResponse, SearchResult)
├── core/         # Chunker, embedder, reranker, retriever, LLM, RAG pipeline
├── db/           # ChromaDB handler, SQLite models
└── ingestion/    # YouTube API, transcript extraction, pipeline, scheduler
eval/             # Labelled questions + offline self-seeding evaluation harness
tests/            # 36 pytest tests covering all core modules and reranking
.github/          # GitHub Actions workflows for PR evaluation quality gate
```

## Key design decisions

**Why Cross-Encoder Reranking?**  
Standard bi-encoders embed queries and documents independently (e.g. cosine distance), which misses token-to-token semantic alignments. A second-stage Cross-Encoder scores query-document pairs jointly, matching complex contextual patterns and boosting retrieval precision by 20-30%.

**Why programmatically Enriched & Enforced Citations?**  
LLMs under text prompts frequently hallucinate sources or omit citations. By forcing structured output via JSON mode (`response_format={"type": "json_object"}`) and programmatically matching citations against retrieved metadata IDs in python, hallucinated sources are stripped before they can reach the user.

**Why chunking over full-transcript embedding**  
Embedding entire transcripts dilutes meaning across topics. 300-token chunks with 50-token overlap keep each embedding focused on one idea, improving retrieval precision significantly.

**Why hybrid search over pure vector search**  
Vector search misses exact terms (a query for "CRISPR" may not retrieve chunks that don't discuss gene editing semantically). BM25 catches exact terms but misses meaning. RRF fusion covers both blind spots.

**Why LiteLLM**  
Provider lock-in is a real production risk. LiteLLM gives a single `completion()` interface over 100+ providers. Switching from Groq to Gemini requires changing one environment variable, not refactoring code.

**Why APScheduler over Celery**  
Celery requires a Redis broker — unnecessary operational complexity for hourly polling at this scale. APScheduler runs in-process. The upgrade path to Celery is clear if throughput demands it.
