from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.models import HealthResponse
from app.config import get_settings
from app.db.sqlite import get_session, list_channels
from app.db.vectordb import VectorDB

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
@router.head("/health")
def health_check(session: Session = Depends(get_session)):
    settings = get_settings()
    db = VectorDB()
    channels = list_channels(session)

    return HealthResponse(
        status="ok",
        chunks_indexed=db.count(),
        channels_tracked=len(channels),
        active_llm=settings.active_llm_model,
    )