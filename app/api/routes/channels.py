from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.models import (
  AddChannelRequest, AddChannelResponse,
  ChannelResponse, VideoResponse,
)
from app.db.sqlite import (
  delete_channel, get_session, get_videos_by_channel, list_channels,
)
from app.db.vectordb import VectorDB
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter()


@router.post("/channels", response_model=AddChannelResponse)
def add_channel(
  request: AddChannelRequest,
  session: Session = Depends(get_session),
):
  try:
    pipeline = IngestionPipeline()
    result = pipeline.add_channel(
      channel_input=request.channel_input,
      max_videos=request.max_videos
    )

    return AddChannelResponse(
      **result,
      message=f"Successfully ingested {result['videos_ingested']}"
    )

  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.get("/channels", response_model=list[ChannelResponse])
def get_channels(session: Session = Depends(get_session)):
  channels = list_channels(session)

  return [
    ChannelResponse(
      youtube_id=ch.youtube_id,
      name=ch.name,
      url=ch.url,
      last_checked_at=ch.last_checked_at.isoformat() if ch.last_checked_at else None,
      created_at=ch.created_at.isoformat(),
    )
    for ch in channels
  ]


@router.get("/channels/{youtube_id}/videos", response_model=list[VideoResponse])
def get_channel_videos(
  youtube_id: str,
  session: Session = Depends(get_session),
):
  videos = get_videos_by_channel(session, youtube_id)
  return [
    VideoResponse(
      youtube_id=v.youtube_id,
      title=v.title,
      description=v.description,
      published_at=v.published_at.isoformat() if v.published_at else None,
      duration_seconds=v.duration_seconds,
      view_count=v.view_count,
      like_count=v.like_count,
      thumbnail_url=v.thumbnail_url,
      ingested=v.ingested,
      ingested_at=v.ingested_at.isoformat() if v.ingested_at else None,
    )
    for v in videos
  ]


@router.delete("/channels/{youtube_id}", status_code=204)
def remove_channel(
  youtube_id: str,
  session: Session = Depends(get_session),
):
  """
  Deletes a channel from SQLite (channel + videos + jobs) and removes
  all its chunks from ChromaDB so the index stays consistent.
  """
  # Collect video IDs *before* deleting from SQLite
  from app.db.sqlite import get_videos_by_channel
  videos = get_videos_by_channel(session, youtube_id)
  video_ids = [v.youtube_id for v in videos]

  # Remove chunks from ChromaDB
  if video_ids:
    try:
      vdb = VectorDB()
      vdb.delete_chunks_for_videos(video_ids)
    except Exception as e:
      print(f"ChromaDB cleanup warning for {youtube_id}: {e}")

  found = delete_channel(session, youtube_id)
  if not found:
    raise HTTPException(status_code=404, detail="Channel not found")

  # Rebuild BM25 index to keep keyword search in sync
  try:
    from app.core.retriever import HybridRetriever
    retriever = HybridRetriever()
    retriever.rebuild_bm25()
  except Exception as e:
    print(f"BM25 index rebuild warning for {youtube_id}: {e}")


@router.post("/videos/{youtube_id}/ingest")
def ingest_video(youtube_id: str):
  """Manually trigger ingestion for a registered video."""
  from app.db.sqlite import get_engine, Video, select
  from app.ingestion.pipeline import IngestionPipeline
  
  engine = get_engine()
  with Session(engine) as session:
    video = session.exec(select(Video).where(Video.youtube_id == youtube_id)).first()
    if not video:
      raise HTTPException(status_code=404, detail="Video not found")
    
    pipeline = IngestionPipeline()
    success = pipeline._ingest_one_video(video.youtube_id, video.title)
    
    if not success:
      raise HTTPException(status_code=500, detail="Ingestion failed")
    
    # Rebuild index
    from app.core.retriever import HybridRetriever
    retriever = HybridRetriever()
    retriever.rebuild_bm25()
    
    return {"status": "ok"}