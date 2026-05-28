# rrf_score(chunk) = 1/(60 + rank_in_bm25) + 1/(60 + rank_in_vector)

import pickle
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.core.embedder import get_embedder
from app.db.vectordb import ChunkResult, VectorDB


# ── BM25 Index ────────────────────────────────────────────────────────────────

class BM25Index:
  """
  Wraps rank-bm25's BM25Okapi.
  """

  def __init__(self):
    settings = get_settings()
    self._index_path = settings.bm25_index_path
    self._bm25: Optional[BM25Okapi] = None
    self._chunk_ids: list[str] = []
    self._chunk_texts: list[str] = []
    self._metadatas: list[dict] = []

  def build(
    self,
    texts: list[str],
    chunk_ids: list[str],
    metadatas: list[dict],
  ) -> None:
    if not texts:
      self._bm25 = None
      self._chunk_ids = []
      self._chunk_texts = []
      self._metadatas = []
      if Path(self._index_path).exists():
        try:
          Path(self._index_path).unlink()
        except Exception as e:
          print(f"Error removing stale BM25 pickle: {e}")
      return

    self._chunk_ids = chunk_ids
    self._chunk_texts = texts
    self._metadatas = metadatas

    tokenised = [text.lower().split() for text in texts]
    self._bm25 = BM25Okapi(tokenised)
    self._save()

  def load(self) -> bool:
    if not Path(self._index_path).exists():
      return False

    with open(self._index_path, "rb") as f:
      data = pickle.load(f)

    self._bm25 = data["bm25"]
    self._chunk_ids = data["chunk_ids"]
    self._chunk_texts = data["chunk_texts"]
    self._metadatas = data["metadatas"]
    return True

  def _save(self) -> None:
    Path(self._index_path).parent.mkdir(parents=True, exist_ok=True)
    with open(self._index_path, "wb") as f:
      pickle.dump({
        "bm25": self._bm25,
        "chunk_ids": self._chunk_ids,
        "chunk_texts": self._chunk_texts,
        "metadatas": self._metadatas,
      }, f)

  def search(
    self,
    query: str,
    top_k: int,
    channel_name: Optional[str] = None,
  ) -> list[tuple[str, float, str, dict]]:
    if self._bm25 is None:
      return []

    tokenised_query = query.lower().split()
    scores = self._bm25.get_scores(tokenised_query)

    scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results = []
    for idx, score in scored:
      if score == 0:
        break

      meta = self._metadatas[idx]

      if channel_name and meta.get("channel_name") != channel_name:
        continue

      results.append((
        self._chunk_ids[idx],
        score,
        self._chunk_texts[idx],
        meta,
      ))

      if len(results) >= top_k:
        break

    return results

  @property
  def is_ready(self) -> bool:
    return self._bm25 is not None


# ── RRF Fusion ────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
  bm25_results: list[tuple[str, float, str, dict]],
  vector_results: list[ChunkResult],
  top_k: int,
  k: int = 60,
) -> list[dict]:
  rrf_scores: dict[str, float] = {}

  for rank, (chunk_id, _score, _text, _meta) in enumerate(bm25_results):
    rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + rank + 1)

  for rank, result in enumerate(vector_results):
    rrf_scores[result.chunk_id] = (
      rrf_scores.get(result.chunk_id, 0) + 1 / (k + rank + 1)
    )

  chunk_data: dict[str, dict] = {}

  for chunk_id, _score, text, meta in bm25_results:
    chunk_data[chunk_id] = {"text": text, "metadata": meta}

  for result in vector_results:
    if result.chunk_id not in chunk_data:
      chunk_data[result.chunk_id] = {
        "text": result.text,
        "metadata": {
          "video_youtube_id": result.video_youtube_id,
          "video_title": result.video_title,
          "channel_name": result.channel_name,
          "chunk_index": result.chunk_index,
        },
      }

  ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

  return [
    {
      "chunk_id": chunk_id,
      "rrf_score": round(score, 6),
      "text": chunk_data[chunk_id]["text"],
      "video_youtube_id": chunk_data[chunk_id]["metadata"]["video_youtube_id"],
      "video_title": chunk_data[chunk_id]["metadata"]["video_title"],
      "channel_name": chunk_data[chunk_id]["metadata"]["channel_name"],
      "chunk_index": chunk_data[chunk_id]["metadata"]["chunk_index"],
    }
    for chunk_id, score in ranked
    if chunk_id in chunk_data
  ]


# ── Hybrid Retriever ──────────────────────────────────────────────────────────

class HybridRetriever:
  def __init__(self):
    self._vectordb = VectorDB()
    self._bm25 = BM25Index()
    self._embedder = get_embedder()
    self._settings = get_settings()

  def load_or_build_bm25(self, channel_name: Optional[str] = None) -> None:
    loaded = self._bm25.load()
    if loaded:
      print(f"BM25 index loaded from disk")
      return

    print("BM25 index not found — building from ChromaDB...")
    self.rebuild_bm25(channel_name)

  def rebuild_bm25(self, channel_name: Optional[str] = None) -> None:
    texts, ids, metadatas = self._vectordb.get_all_chunks_for_bm25(
      channel_name=channel_name
    )

    self._bm25.build(texts=texts, chunk_ids=ids, metadatas=metadatas)

    if not texts:
      print("No chunks in ChromaDB yet — BM25 index cleared")
    else:
      print(f"BM25 index built: {len(texts)} chunks indexed")

  def search(
    self,
    query: str,
    top_k: Optional[int] = None,
    channel_name: Optional[str] = None,
  ) -> list[dict]:
    if top_k is None:
      top_k = self._settings.top_k_results

    candidates = top_k * 2

    query_embedding = self._embedder.embed_one(query)

    bm25_results = self._bm25.search(
      query=query,
      top_k=candidates,
      channel_name=channel_name,
    )

    vector_results = self._vectordb.search(
      query_embedding=query_embedding,
      top_k=candidates,
      channel_name=channel_name,
    )

    return reciprocal_rank_fusion(
      bm25_results=bm25_results,
      vector_results=vector_results,
      top_k=top_k,
    )