# app/db/sqlite.py

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.config import get_settings



class Channel(SQLModel, table=True):
  """
  A YouTube channel the user wants to track.
  One channel → many videos.
  """
  id: Optional[int] = Field(default=None, primary_key=True)
  youtube_id: str = Field(unique=True, index=True) 
  name: str
  url: str                                         
  description: Optional[str] = None
  subscriber_count: Optional[int] = None
  last_checked_at: Optional[datetime] = None       
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )


class Video(SQLModel, table=True):
  """
  A single YouTube video belonging to a channel.
  ingested = True means its chunks are already in ChromaDB.
  This is how the scheduler skips videos it's already processed.
  """
  id: Optional[int] = Field(default=None, primary_key=True)
  youtube_id: str = Field(unique=True, index=True)  
  channel_youtube_id: str = Field(index=True)     
  title: str
  description: Optional[str] = None
  published_at: Optional[datetime] = None
  duration_seconds: Optional[int] = None
  view_count: Optional[int] = None
  like_count: Optional[int] = None
  thumbnail_url: Optional[str] = None
  ingested: bool = Field(default=False)             # has this been chunked + embedded?
  ingested_at: Optional[datetime] = None
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )


class JobStatus(str, Enum):
  PENDING = "pending"
  RUNNING = "running"
  DONE = "done"
  FAILED = "failed"


class IngestionJob(SQLModel, table=True):
  """
  Tracks every ingestion attempt for a video.
  Lets you see what failed, why, and when — essential for debugging
  the scheduled pipeline in production.
  """
  id: Optional[int] = Field(default=None, primary_key=True)
  video_youtube_id: str = Field(index=True)
  status: JobStatus = Field(default=JobStatus.PENDING)
  error_message: Optional[str] = None             
  chunks_created: Optional[int] = None # how many chunks were stored
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )



def get_engine():
  """
  Creates the SQLite engine. check_same_thread=False is required
  because FastAPI handles requests on multiple threads but SQLite
  defaults to single-thread access only.
  """
  settings = get_settings()
  db_url = f"sqlite:///{settings.sqlite_db_path}"
  return create_engine(db_url, connect_args={"check_same_thread": False})


def create_tables() -> None:
  """
  Creates all tables if they don't exist.
  Called once at app startup (in FastAPI lifespan).
  SQLModel.metadata.create_all is idempotent — safe to call every startup.
  """
  engine = get_engine()
  SQLModel.metadata.create_all(engine)

  # Initialize the FTS5 virtual table
  from sqlmodel import text
  with Session(engine) as session:
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


def get_session():
  """
  FastAPI dependency — yields a DB session, closes it after the request.

  Usage in a route:
      @app.get("/channels")
      def list_channels(session: Session = Depends(get_session)):
          ...
  """
  engine = get_engine()
  with Session(engine) as session:
    yield session



def add_channel(session: Session, youtube_id: str, name: str,
                url: str, **kwargs) -> Channel:
  """
  Adds a channel or returns the existing one.
  'Upsert by youtube_id' — safe to call multiple times.
  """
  existing = session.exec(
    select(Channel).where(Channel.youtube_id == youtube_id)
  ).first()

  if existing:
    return existing

  channel = Channel(youtube_id=youtube_id, name=name, url=url, **kwargs)
  session.add(channel)
  session.commit()
  session.refresh(channel)
  return channel


def get_channel_by_youtube_id(session: Session, youtube_id: str) -> Optional[Channel]:
  return session.exec(
    select(Channel).where(Channel.youtube_id == youtube_id)
  ).first()


def list_channels(session: Session) -> list[Channel]:
  return list(session.exec(select(Channel)).all())


def add_video(session: Session, youtube_id: str, channel_youtube_id: str,
              title: str, **kwargs) -> Video:
  """
  Adds a video or returns existing. Same upsert pattern as add_channel.
  The scheduler calls this for every video it discovers — idempotent.
  """
  existing = session.exec(
    select(Video).where(Video.youtube_id == youtube_id)
  ).first()

  if existing:
    return existing

  video = Video(
    youtube_id=youtube_id,
    channel_youtube_id=channel_youtube_id,
    title=title,
    **kwargs
  )
  session.add(video)
  session.commit()
  session.refresh(video)
  return video


def get_uningested_videos(session: Session,
channel_youtube_id: Optional[str] = None) -> list[Video]:
  """
  Returns videos not yet chunked + embedded.
  The scheduler calls this to find work to do.
  Optional filter by channel so we can ingest one channel at a time.
  """
  query = select(Video).where(Video.ingested == False)  # noqa: E712
  if channel_youtube_id:
    query = query.where(Video.channel_youtube_id == channel_youtube_id)
  return list(session.exec(query).all())


def mark_video_ingested(session: Session, youtube_id: str, chunks_created: int) -> None:
  """Called by the ingestion pipeline after successfully storing chunks."""
  video = session.exec(
    select(Video).where(Video.youtube_id == youtube_id)
  ).first()
  if video:
    video.ingested = True
    video.ingested_at = datetime.now(timezone.utc)
    session.add(video)
    session.commit()


def create_job(session: Session, video_youtube_id: str) -> IngestionJob:
  job = IngestionJob(video_youtube_id=video_youtube_id)
  session.add(job)
  session.commit()
  session.refresh(job)
  return job


def update_job(session: Session, job_id: int, status: JobStatus, error_message: Optional[str] = None, chunks_created: Optional[int] = None) -> None:
  job = session.get(IngestionJob, job_id)
  if job:
    job.status = status
    job.updated_at = datetime.now(timezone.utc)
    if error_message:
      job.error_message = error_message
    if chunks_created is not None:
      job.chunks_created = chunks_created
    session.add(job)
    session.commit()


def get_videos_by_channel(session: Session, channel_youtube_id: str) -> list[Video]:
  """Returns all videos for a given channel, ordered newest first."""
  return list(
    session.exec(
      select(Video)
      .where(Video.channel_youtube_id == channel_youtube_id)
      .order_by(Video.published_at.desc())  # type: ignore[arg-type]
    ).all()
  )


def delete_channel(session: Session, youtube_id: str) -> bool:
  """
  Deletes a channel and all its associated videos + ingestion jobs from SQLite.
  Returns True if the channel existed, False otherwise.
  Callers are responsible for removing chunks from ChromaDB separately.
  """
  channel = session.exec(
    select(Channel).where(Channel.youtube_id == youtube_id)
  ).first()

  if not channel:
    return False

  # Delete ingestion jobs for every video in this channel
  videos = session.exec(
    select(Video).where(Video.channel_youtube_id == youtube_id)
  ).all()

  # Collect video IDs for FTS5 cleanup
  video_ids = [video.youtube_id for video in videos]
  if video_ids:
    delete_fts_chunks_for_videos(session, video_ids)

  for video in videos:
    jobs = session.exec(
      select(IngestionJob).where(IngestionJob.video_youtube_id == video.youtube_id)
    ).all()
    for job in jobs:
      session.delete(job)
    session.delete(video)

  session.delete(channel)
  session.commit()
  return True


def insert_fts_chunk(
  session: Session,
  chunk_id: str,
  text_content: str,
  video_youtube_id: str,
  video_title: str,
  channel_name: str,
  chunk_index: int,
  start_second: int,
) -> None:
  """Idempotently insert a chunk into the SQLite FTS5 index."""
  from sqlmodel import text
  # 1. Delete if already exists to keep it idempotent
  session.exec(
    text("DELETE FROM chunk_fts WHERE chunk_id = :cid").bindparams(cid=chunk_id)
  )
  # 2. Insert the new FTS entry
  session.exec(
    text(
      "INSERT INTO chunk_fts (chunk_id, text, video_youtube_id, video_title, channel_name, chunk_index, start_second) "
      "VALUES (:cid, :txt, :vid, :title, :channel, :idx, :start_sec)"
    ).bindparams(
      cid=chunk_id,
      txt=text_content,
      vid=video_youtube_id,
      title=video_title,
      channel=channel_name,
      idx=chunk_index,
      start_sec=start_second,
    )
  )
  session.commit()


def delete_fts_chunks_for_videos(session: Session, video_youtube_ids: list[str]) -> None:
  """Remove all chunks for a list of video IDs from FTS5 index."""
  from sqlmodel import text
  for vid_id in video_youtube_ids:
    session.exec(
      text("DELETE FROM chunk_fts WHERE video_youtube_id = :vid").bindparams(vid=vid_id)
    )
  session.commit()