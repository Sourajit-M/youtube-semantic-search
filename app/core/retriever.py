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
  FTS5 full-text keyword search index backed by SQLite.
  Completely replaces the binary rank-bm25 pickle index.
  """

  def __init__(self):
    from sqlmodel import Session, text
    from app.db.sqlite import get_engine
    self._engine = get_engine()
    
    # Self-healing: create the FTS table if it doesn't exist yet to support isolated tests
    with Session(self._engine) as session:
      session.exec(text(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5("
        "  chunk_id,"
        "  text,"
        "  video_youtube_id,"
        "  video_title,"
        "  channel_name,"
        "  chunk_index UNINDEXED,"
        "  start_second UNINDEXED"
        ");"
      ))
      session.commit()

  def build(
    self,
    texts: list[str],
    chunk_ids: list[str],
    metadatas: list[dict],
  ) -> None:
    """
    Build FTS index by inserting texts into SQLite FTS5 table.
    Ensures unit tests and manual rebuilds work seamlessly.
    """
    from sqlmodel import Session, text
    
    with Session(self._engine) as session:
      session.exec(text("DELETE FROM chunk_fts"))
      session.commit()

    if not texts:
      return

    with Session(self._engine) as session:
      for text_content, cid, meta in zip(texts, chunk_ids, metadatas):
        session.exec(
          text(
            "INSERT INTO chunk_fts (chunk_id, text, video_youtube_id, video_title, channel_name, chunk_index, start_second) "
            "VALUES (:cid, :txt, :vid, :title, :channel, :idx, :start_sec)"
          ).bindparams(
            cid=cid,
            txt=text_content,
            vid=meta["video_youtube_id"],
            title=meta["video_title"],
            channel=meta["channel_name"],
            idx=meta["chunk_index"],
            start_sec=meta.get("start_second", 0),
          )
        )
      session.commit()

  def load(self) -> bool:
    """Always ready since the SQLite FTS5 table is stored directly in metadata.db."""
    return True

  def search(
    self,
    query: str,
    top_k: int,
    channel_name: Optional[str] = None,
  ) -> list[tuple[str, float, str, dict]]:
    """
    FTS5 Full-Text search using SQLite's native bm25() ranking helper function.
    
    SQLite's bm25() function returns a float score where a lower score
    (more negative) indicates a better match. We sort by score ASC.
    """
    if not query.strip():
      return []

    from sqlmodel import Session, text
    import re

    # Extract alphanumeric words and join with OR to mimic standard BM25 multi-keyword matching
    words = re.findall(r'\w+', query)
    if not words:
      return []
    cleaned_query = " OR ".join(words)

    sql = (
      "SELECT chunk_id, text, video_youtube_id, video_title, channel_name, chunk_index, start_second, "
      "bm25(chunk_fts) as score "
      "FROM chunk_fts "
      "WHERE chunk_fts MATCH :query"
    )
    if channel_name:
      sql += " AND channel_name = :channel"
    sql += " ORDER BY score ASC LIMIT :limit"

    with Session(self._engine) as session:
      params = {"query": cleaned_query, "limit": top_k}
      if channel_name:
        params["channel"] = channel_name
      
      try:
        rs = session.exec(text(sql).bindparams(**params)).all()
      except Exception as e:
        print(f"FTS5 Query warning: {e}")
        return []

      results = []
      for r in rs:
        raw_score = r[7]
        # Invert the negative FTS score to return a positive metric (lower score is better, so higher -score is better)
        pos_score = -raw_score if raw_score else 0.0

        results.append((
          r[0],
          pos_score,
          r[1],
          {
            "video_youtube_id": r[2],
            "video_title": r[3],
            "channel_name": r[4],
            "chunk_index": r[5],
            "start_second": int(r[6]) if r[6] is not None else 0,
          }
        ))
      
      return results

  @property
  def is_ready(self) -> bool:
    return True


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
          "start_second": result.start_second,
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
      "start_second": chunk_data[chunk_id]["metadata"].get("start_second", 0),
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

    # Retrieve top-20 candidates from RRF to feed into the reranker
    rrf_candidates_count = 20

    query_embedding = self._embedder.embed_one(query)

    bm25_results = self._bm25.search(
      query=query,
      top_k=rrf_candidates_count,
      channel_name=channel_name,
    )

    vector_results = self._vectordb.search(
      query_embedding=query_embedding,
      top_k=rrf_candidates_count,
      channel_name=channel_name,
    )

    rrf_results = reciprocal_rank_fusion(
      bm25_results=bm25_results,
      vector_results=vector_results,
      top_k=rrf_candidates_count,
    )

    if not rrf_results:
      return []

    # Two-Stage Reranking
    from app.core.reranker import get_reranker
    reranker = get_reranker()

    texts = [r["text"] for r in rrf_results]
    scores = reranker.score(query, texts)

    for r, score in zip(rrf_results, scores):
      r["rerank_score"] = score

    # Sort candidates by rerank_score descending
    reranked_results = sorted(rrf_results, key=lambda x: x["rerank_score"], reverse=True)

    return reranked_results[:top_k]