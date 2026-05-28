from dataclasses import dataclass

from app.config import get_settings
from app.core.llm import call_llm
from app.core.retriever import HybridRetriever

@dataclass
class RAGResponse:
  """
    Everything the API returns for a /ask request.
    answer       — the LLM's response grounded in retrieved chunks
    sources      — the chunks used as evidence (for citations)
    provider     — which LLM actually answered (primary or fallback)
    chunks_used  — how many chunks were in the context window
  """
  answer: str
  sources: list[dict]
  chunks_used: int

_SYSTEM_PROMPT = """
You are an AI assistant that answers questions about YouTube video content.

RULES:
1. Answer ONLY using the provided transcript excerpts as context.
2. If the context doesn't contain enough information to answer, say so clearly.
3. Always mention which video(s) your answer comes from.
4. Be concise and direct. Do not pad your answer.
5. If multiple videos cover the topic, synthesise across them.
"""

def _build_prompt(query: str, chunks: list[dict]) -> str:
  """
  Build the RAG prompt by injecting retrieved chunks as context.

  Format:
      CONTEXT:
      [Source: Video Title]
      chunk text...

      [Source: Another Video]
      chunk text...

      QUESTION:
      user's query

  This format is explicit about sources so the LLM can cite them
  without hallucinating video names.
  """

  context_blocks = []
  for chunk in chunks:
    start_sec = chunk.get("start_second", 0)
    mins = start_sec // 60
    secs = start_sec % 60
    time_str = f"{mins}:{secs:02d}"
    block = f"[Source: {chunk['video_title']} at {time_str}]\n{chunk['text']}"
    context_blocks.append(block)

  context = "\n\n".join(context_blocks)

  return f"""CONTEXT:
  {context}

  QUESTION:
  {query}
  Answer the question using only the context above. Cite the video title(s) you used.
  """

class RAGPipeline:
  """
  Orchestrates the full RAG flow:
  query → retrieve chunks → build prompt → call LLM → return answer + sources

  This is the class the API routes call directly.
  Instantiated once at startup (via get_rag_pipeline singleton).
  """
  
  def __init__(self, retriever: HybridRetriever):
    self._retriever = retriever
    self._settings = get_settings()

  def ask(
    self,
    query: str,
    top_k: int | None = None,
    channel_name: str | None = None
  ) -> RAGResponse:
    """
    Full RAG pipeline in four steps:
    1. Retrieve relevant chunks via hybrid search
    2. Build prompt with chunks as context
    3. Call LLM
    4. Return structured response with sources
    """

    if top_k is None:
      top_k = self._settings.top_k_results

    chunks = self._retriever.search(
      query=query,
      top_k=top_k,
      channel_name=channel_name,
    )

    if not chunks:
      return RAGResponse(
        answer="I couldn't find any relevant content for your question. "
        "Try adding a YouTube channel first.",
        sources=[],
        chunks_used=0,
      )

    prompt = _build_prompt(query, chunks)

    answer = call_llm(prompt=prompt, system_prompt=_SYSTEM_PROMPT)

    # Return with sources
    # Deduplicate sources by video — multiple chunks from same video
    # should appear as one source entry, not five

    

    seen_videos: set[str] = set()
    unique_sources = []
    # chunks are already sorted by rrf_score descending from retriever
    # so first appearance of each video_id = that video's best chunk
    for chunk in chunks:
      vid_id = chunk["video_youtube_id"]
      if vid_id not in seen_videos:
        seen_videos.add(vid_id)
        unique_sources.append({
          "video_youtube_id": vid_id,
          "video_title": chunk["video_title"],
          "channel_name": chunk["channel_name"],
          "rrf_score": chunk["rrf_score"],
          "start_second": chunk.get("start_second", 0),
        })

    return RAGResponse(
      answer=answer,
      sources=unique_sources,
      chunks_used=len(chunks),
    )