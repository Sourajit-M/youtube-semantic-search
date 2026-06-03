from fastapi import APIRouter, HTTPException, Request

from app.api.models import (
  AskRequest, AskResponse, SearchRequest, SearchResponse, SearchResult, SourceVideo, CitationModel
)
from app.config import get_settings

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, req: Request):
  rag = req.app.state.rag_pipeline

  try:
    response = rag.ask(
      query = request.question,
      top_k = request.top_k,
      channel_name = request.channel_name
    )

    settings = get_settings()

    return AskResponse(
      answer = response.answer,
      sources = [
        SourceVideo(**s) for s in response.sources
      ],
      citations = [
        CitationModel(**c) for c in response.citations  # <-- Added mapping
      ],
      chunks_used = response.chunks_used,
      provider = settings.active_llm_model,
    )
  
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))



@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, req: Request):
  retriever = req.app.state.retriever

  try:
    results = retriever.search(
      query=request.query,
      top_k=request.top_k,
      channel_name=request.channel_name,
    )
    return SearchResponse(
      results=[SearchResult(**r) for r in results],
      total=len(results),
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))