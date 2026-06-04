import json
import logging
from dataclasses import dataclass
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.llm import call_llm
from app.core.retriever import HybridRetriever

class Citation(BaseModel):
  video_id: str = Field(description="The exact youtube ID of the video being cited")
  video_title: str = Field(description="The exact title of the video being cited")
  quote: str = Field(description="The exact short quote from the transcript text supporting the answer")

class StructuredAnswer(BaseModel):
  answer: str
  citations: list[Citation]

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
  citations: list[dict]
  chunks_used: int

_STRUCTURED_SYSTEM_PROMPT = """
You are an AI assistant that answers questions about YouTube video content.
RULES:
1. Answer ONLY using the provided transcript excerpts as context.
2. If the context doesn't contain enough information to answer, say so clearly.
3. You must output a JSON object with the following fields:
  - "answer": A string containing the detailed answer to the user query grounded only in the context.
  - "citations": A list of objects, where each object has:
    - "video_id": The exact youtube ID of the video being cited (obtained from the context source header, e.g. "ID: ...").
    - "video_title": The exact title of the video being cited.
    - "quote": A short, exact quote from the transcript text supporting the answer.
4. If no citations are found or needed, set "citations" to an empty list [].
5. Do not include any explanation or markdown outside the JSON object. Output raw JSON only.
"""

def _build_prompt(query: str, chunks: list[dict]) -> str:
  context_blocks = []
  for chunk in chunks:
    start_sec = chunk.get("start_second", 0)
    mins = start_sec // 60
    secs = start_sec % 60
    time_str = f"{mins}:{secs:02d}"
    block = f"[Source: {chunk['video_title']} (ID: {chunk['video_youtube_id']}) at {time_str}]\n{chunk['text']}"
    context_blocks.append(block)

  context = "\n\n".join(context_blocks)

  return f"""CONTEXT:
  {context}

  QUESTION:
  {query}

  Answer the question in the required JSON format.
  """

class RAGPipeline:
  def __init__(self, retriever: HybridRetriever):
    self._retriever = retriever
    self._settings = get_settings()

  def ask(
    self,
    query: str,
    top_k: int | None = None,
    channel_name: str | None = None
  ) -> RAGResponse:
    if top_k is None:
      top_k = self._settings.top_k_results

    chunks = self._retriever.search(
      query=query,
      top_k=top_k,
      channel_name=channel_name,
    )

    if not chunks:
      return RAGResponse(
        answer="I couldn't find any relevant content for your question.",
        sources=[],
        citations=[],
        chunks_used=0,
      )

    prompt = _build_prompt(query, chunks)
    raw_answer = call_llm(
      prompt=prompt,
      system_prompt=_STRUCTURED_SYSTEM_PROMPT,
      response_format={"type" : "json_object"}
    )

    try:
      parsed = json.loads(raw_answer)
    except json.JSONDecodeError as e:
      logging.error(f"Failed to parse LLM JSON: {e}. Raw response: {raw_answer}")
      parsed = {"answer": raw_answer, "citations": []}

    answer_text = parsed.get("answer", "")
    citations_raw = parsed.get("citations", [])

    # Programmatic citation validation
    valid_video_ids = {chunk["video_youtube_id"] for chunk in chunks}
    validated_citations = []

    for cit in citations_raw:
      vid_id = cit.get("video_id")
      if vid_id in valid_video_ids:
        validated_citations.append({
          "video_id": vid_id,
          "video_title": cit.get("video_title", ""),
          "quote": cit.get("quote", "")
        })
      else:
        logging.warning(
          f"Hallucinated citation rejected and stripped: video_id '{vid_id}' not in retrieved chunks!"
        )

    # Deduplicate sources
    seen_videos: set[str] = set()
    unique_sources = []
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
      answer=answer_text,
      sources=unique_sources,
      citations=validated_citations,
      chunks_used=len(chunks),
    )