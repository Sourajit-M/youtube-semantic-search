# 📺 YouTube RAG Engine — LLM Wiki

> A complete reference for how this application works: from raw YouTube URLs to grounded AI answers.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Data Flow: Ingestion Pipeline](#3-data-flow-ingestion-pipeline)
4. [Data Flow: Query Pipeline](#4-data-flow-query-pipeline)
5. [Core Modules Reference](#5-core-modules-reference)
   - [Chunker](#51-chunker)
   - [Embedder](#52-embedder)
   - [BM25 Index (SQLite FTS5)](#53-bm25-index-sqlite-fts5)
   - [Vector Database (ChromaDB)](#54-vector-database-chromadb)
   - [Hybrid Retriever & RRF Fusion](#55-hybrid-retriever--rrf-fusion)
   - [RAG Pipeline](#56-rag-pipeline)
   - [LLM Gateway](#57-llm-gateway)
   - [Video Timestamp Citations](#58-video-timestamp-citations)
6. [Ingestion System](#6-ingestion-system)
   - [YouTube API Layer](#61-youtube-api-layer)
   - [Transcript Extraction](#62-transcript-extraction)
   - [Ingestion Pipeline](#63-ingestion-pipeline)
   - [Background Scheduler](#64-background-scheduler)
7. [Database Layer](#7-database-layer)
   - [SQLite (Metadata)](#71-sqlite-metadata)
   - [ChromaDB (Vectors)](#72-chromadb-vectors)
   - [BM25 Index (SQLite FTS5 Virtual Table)](#73-bm25-index-sqlite-fts5-virtual-table)
8. [API Reference](#8-api-reference)
9. [Configuration & Environment](#9-configuration--environment)
10. [Evaluation Harness](#10-evaluation-harness)
11. [Key Design Decisions](#11-key-design-decisions)
12. [Glossary](#12-glossary)

---

## 1. What This System Does

YouTube RAG Engine is a **Retrieval-Augmented Generation (RAG)** system. Given any YouTube channel or video URL, it:

1. Downloads and indexes the video transcripts.
2. Stores them as searchable chunks in a hybrid search index (vector + keyword).
3. Accepts natural-language questions.
4. Retrieves the most relevant transcript chunks.
5. Sends those chunks as context to an LLM to generate a grounded, cited answer.

The key guarantee: **answers are grounded in real transcript content**, not hallucinated from the LLM's training data.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Streamlit UI (main.py)              │
│         Ask questions ─── Manage channels               │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST
┌───────────────────────▼─────────────────────────────────┐
│              FastAPI Backend (app/api/)                  │
│   POST /channels   POST /ask   POST /search   GET /health│
└──────┬────────────────┬────────────────────────────────-─┘
       │                │
  ┌────▼────┐     ┌─────▼──────────────────────────────┐
  │Ingestion│     │           RAG Query Path            │
  │Pipeline │     │  HybridRetriever → RAGPipeline      │
  └────┬────┘     └───────┬──────────┬──────────────────┘
       │                  │          │
  ┌────▼──────┐   ┌───────▼──┐ ┌────▼──────────────┐
  │ YouTube   │   │ ChromaDB │ │  BM25 Index        │
  │ API+yt-dlp│   │(vectors) │ │ (SQLite FTS5)      │
  └────┬──────┘   └──────────┘ └────────────────────┘
       │
  ┌────▼──────────────┐   ┌──────────────────────────┐
  │ SQLite (metadata) │   │  LiteLLM → Groq / Gemini  │
  └───────────────────┘   └──────────────────────────┘
```

---

## 3. Data Flow: Ingestion Pipeline

This is triggered when a user adds a channel or video URL.

```
User Input (URL / handle)
        │
        ▼
extract_video_id()  ──── Is it a video URL? ─────► _add_single_video()
        │ No                                              │
        ▼                                                 │
resolve_channel_id()  ← YouTube Data API v3              │
        │                                                 │
        ▼                                                 │
fetch_channel_videos() → list of video metadata          │
        │                                                 │
        ▼                                                 │
SQLite: add_channel() + add_video() (upsert, idempotent) │
        │◄────────────────────────────────────────────────┘
        ▼
For each uningested video:
  fetch_transcript(video_id)  ← yt-dlp downloads .vtt file
        │
        ▼
  _parse_vtt()  → clean plain-text transcript string
        │
        ▼
  TranscriptChunker.chunk_texts()
  300-token windows, 50-token overlap
        │
        ▼
  Embedder.embed(chunks)
  all-MiniLM-L6-v2 → 384-dim float vectors
        │
        ▼
  VectorDB.upsert_chunks()  → ChromaDB (HNSW cosine index)
        │
        ▼
  SQLite: mark_video_ingested()
        │
        ▼
  HybridRetriever.rebuild_bm25()  → SQLite FTS5 index refreshed
```

---

## 4. Data Flow: Query Pipeline

Triggered on every `POST /ask` or `POST /search` request.

```
User Question (string)
        │
        ▼
HybridRetriever.search(query, top_k, channel_name?)
        │
        ├──────────────────────────────────┐
        │                                  │
        ▼                                  ▼
Embedder.embed_one(query)         BM25Index.search(query)
→ 384-dim query vector            → tokenised exact-term search
        │                                  │
        ▼                                  │
VectorDB.search(embedding, top_k*2)        │
→ ChromaDB HNSW cosine search             │
        │                                  │
        └──────────────┬───────────────────┘
                       │
                       ▼
        reciprocal_rank_fusion(bm25_results, vector_results)
        RRF score = 1/(60+rank_bm25) + 1/(60+rank_vector)
        → top_k merged, deduplicated chunks
                       │
                       ▼
        _build_prompt(query, chunks)
        Injects chunks as [Source: Video Title] blocks
                       │
                       ▼
        call_llm(prompt, system_prompt)
        → LiteLLM → Groq (primary) or Gemini (fallback)
                       │
                       ▼
        RAGResponse(answer, sources, chunks_used)
        Sources deduplicated by video (best RRF chunk per video)
                       │
                       ▼
        AskResponse → JSON to client
```

---

## 5. Core Modules Reference

### 5.1 Chunker

**File:** `app/core/chunker.py`

Splits a raw transcript string into overlapping token windows.

| Parameter | Default | Description |
|---|---|---|
| `chunk_size` | 300 | Max words per chunk |
| `chunk_overlap` | 50 | Words shared between adjacent chunks |
| `step` | 250 | Stride = chunk_size − overlap |

**Pre-processing:** Collapses whitespace, strips `[bracketed annotations]`.

**Edge cases:**
- Transcripts < 30 words → returned as a single chunk.
- Trailing windows < 30 words → discarded (avoids noise chunks).

**Output:** `list[Chunk]` — each has `.text`, `.chunk_index`, `.start_token`, `.end_token`.

**Why 300/50?** A 300-word window covers ~2–3 minutes of speech — enough context for a coherent idea. 50-word overlap prevents answers from being split across chunk boundaries.

### 5.2 Embedder

**File:** `app/core/embedder.py`

Wraps FastEmbed's ONNX runtime embedding model.

| Property | Value |
|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Runtime | ONNX (CPU-only, no PyTorch) |
| RAM | ~200 MB vs ~2 GB for PyTorch |

**Key methods:**
- `embed(texts: list[str]) → list[list[float]]` — batch embed (more efficient).
- `embed_one(text: str) → list[float]` — convenience wrapper for a single query.

**Singleton:** `get_embedder()` is `@lru_cache` — model loads once per process.

**Important:** Both documents (at ingest time) and queries (at search time) are embedded using the same model. Cosine similarity comparisons are only valid when both vectors live in the same embedding space.

---

### 5.3 BM25 Index (SQLite FTS5)

**File:** `app/core/retriever.py` → `class BM25Index`

A database-level keyword search index using SQLite's native FTS5 (Full-Text Search) module. It completely replaces the insecure, thread-unsafe binary `pickle` implementation.

**Lifecycle & Syncing:**
1. **Startup:** Zero-latency startup. FTS5 tables (`chunk_fts`) are persisted directly inside the SQLite database (`metadata.db`).
2. **Incremental Indexing:** Chunks are written directly to FTS5 at ingestion time via `insert_fts_chunk(...)`.
3. **Incremental Deletion:** Chunks are deleted instantly when channels/videos are removed via `delete_fts_chunks_for_videos(...)`.
4. **Self-Healing:** If the FTS5 table is missing (e.g. during isolated unit tests), the `BM25Index` constructor automatically recreates it.

**Scoring:**
FTS5 uses SQLite's highly optimized, native C-level `bm25(chunk_fts)` auxiliary function. It scores term frequency saturation and document length normalization natively in SQL, ordering matches by `score ASC` (since FTS5 BM25 returns negative relevance values).

**Query Expansion:**
Incoming search queries are regex-parsed into clean alphanumeric word lists joined with `OR` (e.g., `'plate OR tectonics'`). This mimics standard BM25 behavior, matching chunks containing *any* of the keywords and ranking multi-word matches at the top.

---

### 5.4 Vector Database (ChromaDB)

**File:** `app/db/vectordb.py`

Persistent local vector store using ChromaDB's HNSW index.

| Property | Value |
|---|---|
| Collection | `video_chunks` |
| Distance metric | Cosine |
| Storage | `./data/vectordb/` (persistent on disk) |
| Telemetry | Disabled |

**Chunk ID format:** `{video_youtube_id}_chunk_{index}` — e.g. `dQw4w9WgXcQ_chunk_12`

**Metadata stored per chunk:**
```json
{
  "video_youtube_id": "dQw4w9WgXcQ",
  "video_title": "Never Gonna Give You Up",
  "channel_name": "Rick Astley",
  "chunk_index": 12
}
```

**Key operations:**
- `upsert_chunks()` — idempotent write (safe to re-ingest).
- `search()` — ANN query using HNSW, with optional `channel_name` pre-filter.
- `get_all_chunks_for_bm25()` — full scan used to rebuild BM25 index.
- `delete_chunks_for_videos()` — used when a channel is deleted.

---

### 5.5 Hybrid Retriever & RRF Fusion

**File:** `app/core/retriever.py` → `class HybridRetriever`, `reciprocal_rank_fusion()`

The central search component. Combines BM25 and vector search results using **Reciprocal Rank Fusion (RRF)**.

**RRF Formula:**

```
rrf_score(chunk) = 1 / (60 + rank_in_bm25) + 1 / (60 + rank_in_vector)
```

- `k=60` is a standard smoothing constant (prevents top-ranked items from dominating).
- A chunk appearing in **both** result lists gets additive scores from each rank.
- Chunks only in one list still appear in the merged output.

**Search flow:**
1. Embed query → 384-dim vector.
2. BM25 search with `top_k * 2` candidates.
3. ChromaDB vector search with `top_k * 2` candidates.
4. RRF fusion → sorted by merged score → return top `top_k`.

**Why double candidates (top_k * 2)?** To give RRF enough material to work with. If you only fetch `top_k` from each, RRF has nothing to promote from either list.

**Why BM25 + Vector?**
- Vector search: catches semantic similarity ("automobile" matches "car").
- BM25: catches exact terms ("CRISPR" matches "CRISPR", even if the vector space doesn't align).
- Together: covers both blind spots.

---

### 5.6 RAG Pipeline

**File:** `app/core/rag.py` → `class RAGPipeline`

Orchestrates the query-to-answer flow.

**System prompt (hardcoded):**
```
You are an AI assistant that answers questions about YouTube video content.
Rules:
1. Answer ONLY using the provided transcript excerpts.
2. If the context doesn't contain enough information, say so.
3. Always mention which video(s) your answer comes from.
4. Be concise and direct.
5. If multiple videos cover the topic, synthesise across them.
```

**Prompt template:**
```
CONTEXT:
[Source: Video Title]
chunk text...

[Source: Another Video]
chunk text...

QUESTION:
user's query
Answer the question using only the context above. Cite the video title(s) you used.
```

**Source deduplication:** Multiple chunks from the same video are collapsed into a single source citation. The chunk with the highest RRF score is used (chunks are already sorted).

**Empty context guard:** If no chunks are retrieved (no videos ingested), returns a helpful message without calling the LLM.

**Singleton:** `RAGPipeline` is instantiated once at startup via FastAPI's `lifespan` context and stored in `app.state`.

---

### 5.7 LLM Gateway

**File:** `app/core/llm.py`

Thin wrapper over LiteLLM with primary + fallback provider logic.

| Config | Default |
|---|---|
| Primary provider | `groq` |
| Primary model | `groq/llama-3.3-70b-versatile` |
| Fallback provider | `gemini` |
| Fallback model | `gemini/gemini-2.5-flash` |
| Temperature | `0.2` (low — factual, grounded answers) |
| Max tokens | `1024` |

**Fallback logic:** If the primary `completion()` call raises any exception, the fallback model is tried. If both fail, a `RuntimeError` is raised with both error messages.

**Provider switching:** Change `LLM_PROVIDER` in `.env` to swap between `groq` and `gemini` without any code changes.

---

### 5.8 Video Timestamp Citations

**Files:** `app/ingestion/transcripts.py`, `app/core/chunker.py`, `app/ingestion/pipeline.py`, `app/core/rag.py`, `main.py`

Preserves subtitle timestamps from raw YouTube WebVTT files throughout the ingestion and query pipelines, creating clickable YouTube citations.

**The Pipeline Flow:**
1. **Timing Capture (`transcripts.py`):** `_parse_vtt` parses cue intervals (e.g. `00:01:23.450` $\rightarrow$ `83` seconds) and prefixes transcript lines with temporal tags: `[t=83] hello world`.
2. **Negative Lookahead Preservation (`chunker.py`):** The cleaning regex is updated with a negative lookahead to strip generic annotations (like `[Music]`) but preserve timing tags: `re.sub(r'\[(?!t=\d+\])[^\]]*\]', '', text)`.
3. **Extraction & Vector Cleaning (`pipeline.py`):** The pipeline scans for the first `[t=seconds]` tag to set `start_second` in metadata. It then strips all timing tags (`re.sub(r'\[t=\d+\]', '', text)`) so the embedder and database receive clean, natural text for vector search.
4. **Retrieval & RRF Fusion (`retriever.py`):** Chunks returned by ChromaDB or FTS5 carry `start_second` in their metadata.
5. **LLM Citation & UI Linkage (`rag.py` & `main.py`):** We format start seconds as `MM:SS` (e.g., `at 1:24`) and inject them into RAG context blocks. In the Streamlit UI, YouTube links are appended with exact query strings: `&t={start_second}s`.

---

## 6. Ingestion System

### 6.1 YouTube API Layer

**File:** `app/ingestion/youtube_api.py`

Uses Google's `youtube-data-v3` client to fetch channel and video metadata.

**Input resolution logic:**
```
Input string
  │
  ├── Matches YouTube watch/embed URL? → extract video ID → single-video path
  ├── Matches raw 11-char ID?          → single-video path
  ├── Matches UC... channel ID?        → direct channels.list() lookup
  └── Otherwise                        → treated as @handle → forHandle lookup
```

**Video metadata fetched:** `youtube_id`, `channel_id`, `title`, `description` (first 500 chars), `published_at`, `thumbnail_url`, `duration_seconds`, `view_count`, `like_count`.

**Duration parsing:** ISO 8601 duration string `PT1H23M45S` → seconds (e.g., 5025).

**Channel video listing:** Uses the uploads playlist of a channel for efficient paginated listing. Fetches rich metadata via a secondary `videos().list()` call per page.

---

### 6.2 Transcript Extraction

**File:** `app/ingestion/transcripts.py`

Downloads transcripts using `yt-dlp` (not the YouTube API, which has limited transcript access).

**Command used:**
```bash
yt-dlp --write-auto-sub --write-sub --sub-lang en --sub-format vtt \
       --skip-download --js-runtimes node --quiet -o <tmpdir>/<id>.vtt <url>
```

**Priority:** Manual subtitles preferred over auto-generated captions (`--write-sub` before `--write-auto-sub`).

**VTT parsing (`_parse_vtt`):**
1. Decodes bytes as UTF-8 with `errors='replace'` (handles Windows encoding issues).
2. Iterates `webvtt` captions, strips HTML tags (`<c>`, `<00:00:01>` etc.).
3. Deduplicates lines using a `seen` set (auto-captions repeat lines across cue boundaries).
4. Joins all unique lines into a single space-separated string.

**Transcript validation:** Transcripts shorter than 50 words are rejected as too short to produce meaningful chunks.

---

### 6.3 Ingestion Pipeline

**File:** `app/ingestion/pipeline.py` → `class IngestionPipeline`

Properties:
- **Idempotent:** Re-running on an already-ingested video is a no-op (SQLite upsert guard).
- **Resumable:** Each video gets an `IngestionJob` record — failures are tracked per-video, not per-batch.
- **Observable:** Job status transitions: `PENDING → RUNNING → DONE | FAILED`.

**Per-video flow:**
```python
transcript = fetch_transcript(video_id)          # yt-dlp
chunks = chunker.chunk_texts(transcript)          # 300-token windows
embeddings = embedder.embed(chunks)               # 384-dim vectors
vectordb.upsert_chunks(chunks, embeddings, ...)   # → ChromaDB
mark_video_ingested(session, video_id, len(chunks))
update_job(session, job_id, JobStatus.DONE)
```

**After batch completion:** `HybridRetriever.rebuild_bm25()` is called once after all videos in a batch are processed (not per-video, for efficiency).

---

### 6.4 Background Scheduler

**File:** `app/ingestion/scheduler.py`

Uses `APScheduler`'s `BackgroundScheduler` to run `pipeline.run_scheduled_check()` on a configurable interval (default: every 60 minutes).

**Scheduled check logic:**
1. Fetch the 10 most recent videos per tracked channel from YouTube API.
2. `add_video()` any new ones to SQLite (upsert — existing videos untouched).
3. Ingest any newly discovered videos.
4. Update `channel.last_checked_at` timestamp.

**Why APScheduler over Celery:** No external broker (Redis) needed. Runs in a daemon thread inside the FastAPI process. Celery would be the upgrade path for distributed workers or high-throughput jobs.

**Startup/shutdown:** Scheduler starts in the FastAPI `lifespan` context manager and is gracefully shut down (`wait=False`) on app shutdown.

---

## 7. Database Layer

### 7.1 SQLite (Metadata)

**File:** `app/db/sqlite.py`  
**Path:** `./data/metadata.db`  
**ORM:** SQLModel (Pydantic + SQLAlchemy)

**Tables:**

#### `Channel`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | Auto |
| `youtube_id` | str unique | e.g. `UCxxxxxx` |
| `name` | str | Display name |
| `url` | str | Original input URL |
| `last_checked_at` | datetime? | Updated by scheduler |
| `created_at` | datetime | UTC |

#### `Video`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | Auto |
| `youtube_id` | str unique | 11-char video ID |
| `channel_youtube_id` | str FK | Links to Channel |
| `title` | str | |
| `ingested` | bool | `False` until chunks stored in ChromaDB |
| `ingested_at` | datetime? | Set when ingested |
| `duration_seconds` | int? | |
| `view_count` | int? | |
| `like_count` | int? | |

#### `IngestionJob`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | Auto |
| `video_youtube_id` | str | References Video |
| `status` | enum | `pending/running/done/failed` |
| `error_message` | str? | Set on failure |
| `chunks_created` | int? | Set on success |

**Thread safety:** `check_same_thread=False` — FastAPI uses multiple threads; SQLite's default single-thread enforcement is disabled.

---

### 7.2 ChromaDB (Vectors)

**File:** `app/db/vectordb.py`  
**Path:** `./data/vectordb/`  
**Index:** HNSW with cosine distance

Single collection `video_chunks`. Each document is a chunk string with its 384-dim embedding and metadata. Chunk IDs are deterministic: `{video_id}_chunk_{n}` — this makes upserts safe (re-ingesting a video overwrites its old chunks cleanly).

---

### 7.3 BM25 Index (SQLite FTS5 Virtual Table)

**Table Name:** `chunk_fts`  
**Storage:** Contained natively inside `./data/metadata.db`

**Schema:**
```sql
CREATE VIRTUAL TABLE chunk_fts USING fts5(
    chunk_id,               -- The text index key
    text,                   -- The transcript content (INDEXED)
    video_youtube_id,       -- Video mapping (INDEXED)
    video_title,            -- Video mapping (INDEXED)
    channel_name,           -- Channel mapping (INDEXED)
    chunk_index UNINDEXED,  -- Stored but skipped by search index tree
    start_second UNINDEXED  -- Stored but skipped by search index tree
);
```

Keyword indexing is transaction-safe, thread-safe, supports concurrent writes, and updates incrementally!

---

## 8. API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### `GET /health`
Returns system status.
```json
{
  "status": "ok",
  "chunks_indexed": 412,
  "channels_tracked": 3,
  "active_llm": "groq/llama-3.3-70b-versatile"
}
```

### `POST /channels`
Add a channel or video URL for ingestion.
```json
// Request
{ "channel_input": "@crashcourse", "max_videos": 10 }

// Response
{
  "channel_id": "UCxxxxxx",
  "channel_name": "CrashCourse",
  "videos_found": 10,
  "videos_ingested": 9,
  "videos_failed": 1,
  "message": "..."
}
```

### `GET /channels`
List all tracked channels.

### `DELETE /channels/{youtube_id}`
Remove a channel, its videos (SQLite), and all its chunks (ChromaDB). Returns `204 No Content`.

### `GET /channels/{youtube_id}/videos`
List all videos for a channel with ingestion status.

### `POST /ask`
Ask a natural-language question.
```json
// Request
{
  "question": "How was the Earth formed?",
  "channel_name": "CrashCourse",   // optional filter
  "top_k": 5
}

// Response
{
  "answer": "According to Crash Course Geology #2...",
  "sources": [
    {
      "video_youtube_id": "abc123",
      "video_title": "How did Earth form? Crash Course Geology #2",
      "channel_name": "CrashCourse",
      "rrf_score": 0.031746
    }
  ],
  "chunks_used": 5,
  "provider": "groq/llama-3.3-70b-versatile"
}
```

### `POST /search`
Raw chunk search (no LLM call). Returns the top-k chunks directly.
```json
// Request
{ "query": "plate tectonics", "top_k": 5 }

// Response
{
  "results": [
    {
      "chunk_id": "abc123_chunk_4",
      "video_youtube_id": "abc123",
      "video_title": "...",
      "channel_name": "...",
      "text": "...raw chunk text...",
      "rrf_score": 0.031,
      "chunk_index": 4
    }
  ],
  "total": 5
}
```

### `POST /videos/{youtube_id}/ingest`
Trigger ingestion for a single un-ingested video (used by the UI "Index ↗" button).

---

## 9. Configuration & Environment

All settings in `.env`. Loaded via `pydantic-settings` (type-safe, validated).

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Primary LLM provider |
| `LLM_FALLBACK_PROVIDER` | `gemini` | Fallback if primary fails |
| `GROQ_API_KEY` | — | Required for Groq |
| `GEMINI_API_KEY` | — | Required for Gemini fallback |
| `YOUTUBE_API_KEY` | — | YouTube Data API v3 key |
| `CHUNK_SIZE` | `300` | Words per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap words between chunks |
| `TOP_K_RESULTS` | `5` | Default chunks retrieved per query |
| `CHROMA_DB_PATH` | `./data/vectordb` | ChromaDB persistence path |
| `SQLITE_DB_PATH` | `./data/metadata.db` | SQLite path |
| `INGEST_INTERVAL_MINUTES` | `60` | Scheduler polling interval |

**Settings singleton:** `get_settings()` is `@lru_cache` — loaded once per process.

---

## 10. Evaluation Harness

**Files:** `eval/run_eval.py`, `eval/questions.json`

A labelled question set with two metrics:

### Metrics

| Metric | Definition |
|---|---|
| **Hit rate** | Did the expected source video title appear in `response.sources`? |
| **Keyword rate** | Does the answer text contain at least one expected keyword? |

### Quality thresholds

| Hit Rate | Rating |
|---|---|
| ≥ 80% | GOOD |
| 60–79% | FAIR — consider tuning `chunk_size` |
| < 60% | POOR — check ingestion and embeddings |

### Example question entry
```json
{
  "id": "q01",
  "question": "How was the Earth formed?",
  "expected_source": "How did Earth form?: Crash Course Geology #2",
  "keywords": ["solar system", "gas", "dust", "4.6 billion"]
}
```

### Running the eval
```bash
uv run python eval/run_eval.py
```

---

## 11. Key Design Decisions

### Why chunking over full-transcript embedding?
Embedding a 40-minute lecture transcript as a single vector dilutes all topics into one averaged direction. A query about "plate tectonics" then competes against "rock formation", "volcanoes", and everything else in the lecture. 300-word chunks keep each embedding focused on one idea → better retrieval precision.

### Why hybrid search (BM25 + Vector) over pure vector?
- **Vector only:** Misses exact terms. A query for "CRISPR" may not retrieve chunks that don't use "gene editing" semantically.
- **BM25 only:** Misses meaning. "car" won't match "automobile".
- **RRF fusion:** Covers both. Chunks appearing in both rankings get double-boosted scores.

### Why LiteLLM?
Provider lock-in is a production risk. LiteLLM provides one `completion()` interface over 100+ providers. Switching from Groq to Gemini requires changing one env variable, not refactoring code.

### Why APScheduler over Celery?
Celery requires a Redis broker — operational overhead for hourly polling. APScheduler runs in-process in a daemon thread. The upgrade path to Celery is straightforward if throughput demands it.

### Why FastEmbed over sentence-transformers?
- ONNX runtime: ~200 MB RAM vs ~2 GB for PyTorch.
- Same model weights (`all-MiniLM-L6-v2`), identical vectors.
- CPU-only: works on any free cloud tier without GPU.
- Faster cold start — critical for API startup time.

### Why SQLite over PostgreSQL?
Local-first, zero-infrastructure metadata store. SQLModel (SQLAlchemy under the hood) provides a clean migration path to PostgreSQL for production with minimal code changes.

### Why yt-dlp over the YouTube Transcript API?
`yt-dlp` handles auto-generated captions, multiple subtitle tracks, and encoding quirks. The YouTube Transcript API is simpler but fails on many channels (disabled captions, rate limits, regional restrictions).

---

## 12. Glossary

| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation — grounding LLM answers in retrieved documents |
| **Chunk** | A 300-word sliding window of a transcript |
| **Embedding** | A 384-dimensional float vector representing the semantic content of a text |
| **HNSW** | Hierarchical Navigable Small World — the ANN graph index used by ChromaDB |
| **BM25** | Best Match 25 — a probabilistic keyword ranking algorithm (TF-IDF variant) |
| **RRF** | Reciprocal Rank Fusion — merges multiple ranked lists into one unified ranking |
| **Upsert** | Insert or update — idempotent write operation (safe to repeat) |
| **ANN** | Approximate Nearest Neighbor — fast similarity search over vector spaces |
| **VTT** | Web Video Text Tracks — subtitle format downloaded by yt-dlp |
| **LiteLLM** | Python library providing a unified interface to 100+ LLM APIs |
| **FastEmbed** | ONNX-based embedding library by Qdrant (CPU-only, lightweight) |
| **ChromaDB** | Open-source local vector database with persistent HNSW indexing |
| **SQLModel** | ORM combining Pydantic validation with SQLAlchemy persistence |
| **APScheduler** | Python background job scheduler (in-process, no broker required) |
| **Top-K** | The number of chunks retrieved for a given query (configurable, default 5) |
| **Hit Rate** | Eval metric: % of questions where the expected source video was retrieved |

---

## 13. Deployment Guide (Free)

The easiest way to deploy this app for free is using **Hugging Face Spaces** with Docker.

### Step 1: Prepare the Repository
Ensure your repository contains:
- `Dockerfile` (configured to run both API and UI)
- `start.sh` (entry point script)
- `pyproject.toml` and `uv.lock`

### Step 2: Create a Hugging Face Space
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Give your Space a name.
3. Select **Docker** as the SDK.
4. Choose the "Blank" template.
5. Set the Space to **Public** or **Private**.

### Step 3: Configure Environment Variables
In your Space settings, add the following secrets:
- `GROQ_API_KEY`: Your Groq API key.
- `GEMINI_API_KEY`: Your Gemini API key.
- `YOUTUBE_API_KEY`: Your YouTube Data API v3 key.
- `API_URL`: Set to `http://localhost:8000` (internal container URL).

### Step 4: Push to Hugging Face
Link your GitHub repository or upload the files directly. Hugging Face will automatically build the Docker image and start the services.

### Alternative: Render.com (Free Tier)
1. Deploy the FastAPI backend as a **Web Service**.
2. Deploy the Streamlit frontend as another **Web Service**.
3. Point the frontend to the backend's URL via the `API_URL` environment variable.
*Note: Render's free tier spins down after inactivity, causing a slow initial load.*
