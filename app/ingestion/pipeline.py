from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.core.chunker import TranscriptChunker
from app.core.embedder import get_embedder
from app.db.sqlite import (
  JobStatus, add_channel, add_video, create_job,
  get_engine, get_uningested_videos, list_channels,
  mark_video_ingested, update_job,
)
from app.db.vectordb import VectorDB
from app.ingestion.youtube_api import (
  fetch_channel_videos, resolve_channel_id,
  extract_video_id, fetch_video_details_by_id, fetch_channel_info
)
from app.ingestion.transcripts import fetch_transcript


class IngestionPipeline:
  """
  Orchestrates the full ingest flow:
  channel URL → video list → transcripts → chunks → embeddings → storage

  Designed to be:
  - Idempotent: safe to run multiple times, skips already-ingested videos
  - Resumable: each video is tracked via IngestionJob — failures don't
    lose progress, just mark that video as failed for retry
  - Observable: every step updates job status so you can monitor progress
  """

  def __init__(self):
    self._chunker = TranscriptChunker()
    self._embedder = get_embedder()
    self._vectordb = VectorDB()
    self._engine = get_engine()

  # ── Public interface ──────────────────────────────────────────────────────

  def add_channel(self, channel_input: str, max_videos: int = 50) -> dict:
    """
    Register a new channel and ingest its videos.
    Entry point for the POST /channels API endpoint.

    Can also handle a single video URL.
    """
    video_id = extract_video_id(channel_input)

    if video_id:
      return self._add_single_video(video_id)

    print(f"Resolving channel: {channel_input}")
    channel_id, channel_name = resolve_channel_id(channel_input)

    with Session(self._engine) as session:
      channel = add_channel(
        session,
        youtube_id=channel_id,
        name=channel_name,
        url=channel_input,
      )
      print(f"Channel registered: {channel_name} ({channel_id})")

    # Fetch and register videos (metadata only, no transcripts yet)
    print(f"Fetching up to {max_videos} videos...")
    videos = fetch_channel_videos(channel_id, max_results=max_videos)

    with Session(self._engine) as session:
      for v in videos:
        add_video(
          session,
          youtube_id=v["youtube_id"],
          channel_youtube_id=channel_id,
          title=v["title"],
          description=v.get("description"),
          published_at=v.get("published_at"),
          duration_seconds=v.get("duration_seconds"),
          view_count=v.get("view_count"),
          like_count=v.get("like_count"),
          thumbnail_url=v.get("thumbnail_url"),
        )

    print(f"Registered {len(videos)} videos. Starting ingestion...")

    # Ingest all videos for this channel
    results = self._ingest_channel_videos(channel_id)

    return {
      "channel_id": channel_id,
      "channel_name": channel_name,
      "videos_found": len(videos),
      **results,
    }

  def _add_single_video(self, video_id: str) -> dict:
    """Ingest a single video regardless of channel."""
    print(f"Single video ingestion: {video_id}")
    v = fetch_video_details_by_id(video_id)
    channel_id = v["channel_id"]

    # Ensure channel exists
    ch_info = fetch_channel_info(channel_id)
    with Session(self._engine) as session:
      channel = add_channel(
        session,
        youtube_id=channel_id,
        name=ch_info["title"],
        url=f"https://youtube.com/channel/{channel_id}"
      )

      # Register the video
      add_video(
        session,
        youtube_id=video_id,
        channel_youtube_id=channel_id,
        title=v["title"],
        description=v.get("description"),
        published_at=v.get("published_at"),
        duration_seconds=v.get("duration_seconds"),
        view_count=v.get("view_count"),
        like_count=v.get("like_count"),
        thumbnail_url=v.get("thumbnail_url"),
      )

    success = self._ingest_one_video(video_id, v["title"])

    if success:
      from app.core.retriever import HybridRetriever
      retriever = HybridRetriever()
      retriever.rebuild_bm25()

    return {
      "channel_id": channel_id,
      "channel_name": ch_info["title"],
      "videos_found": 1,
      "videos_ingested": 1 if success else 0,
      "videos_failed": 0 if success else 1,
    }

  def run_scheduled_check(self) -> None:
    """
    Called by APScheduler every hour.
    Checks all tracked channels for new videos and ingests them.
    """
    with Session(self._engine) as session:
      channels = list_channels(session)

    if not channels:
      return

    print(f"Scheduled check: {len(channels)} channel(s)")

    for channel in channels:
      try:
        self._check_channel_for_new_videos(channel.youtube_id)
      except Exception as e:
        print(f"Scheduled check failed for {channel.name}: {e}")

  # ── Internal methods ──────────────────────────────────────────────────────

  def _check_channel_for_new_videos(self, channel_id: str) -> None:
    """
    Fetch latest videos from YouTube and register any new ones.
    Then ingest any uningested videos.
    We only fetch the 10 most recent — efficient for hourly polling.
    """
    recent_videos = fetch_channel_videos(channel_id, max_results=10)

    with Session(self._engine) as session:
      for v in recent_videos:
        add_video(
          session,
          youtube_id=v["youtube_id"],
          channel_youtube_id=channel_id,
          title=v["title"],
          **{k: v.get(k) for k in [
            "description", "published_at", "duration_seconds",
            "view_count", "like_count", "thumbnail_url"
          ]},
        )

    self._ingest_channel_videos(channel_id)

    # Update last_checked_at
    with Session(self._engine) as session:
      from app.db.sqlite import get_channel_by_youtube_id
      channel = get_channel_by_youtube_id(session, channel_id)
      if channel:
        channel.last_checked_at = datetime.now(timezone.utc)
        session.add(channel)
        session.commit()

  def _ingest_channel_videos(self, channel_id: str) -> dict:
    """
    Ingest all uningested videos for a channel.
    Returns summary stats.
    """
    with Session(self._engine) as session:
      pending = get_uningested_videos(session, channel_id)

    print(f"Videos pending ingestion: {len(pending)}")

    succeeded = 0
    failed = 0

    for video in pending:
      success = self._ingest_one_video(video.youtube_id, video.title)
      if success:
        succeeded += 1
      else:
        failed += 1

    if succeeded > 0:
      from app.core.retriever import HybridRetriever
      retriever = HybridRetriever()
      retriever.rebuild_bm25()
      print(f"BM25 index rebuilt after ingesting {succeeded} videos")

    return {"videos_ingested": succeeded, "videos_failed": failed}

  def _ingest_one_video(self, video_id: str, title: str) -> bool:
    """
    Full pipeline for one video:
    transcript → clean → chunk → embed → store in ChromaDB → mark ingested
    """
    with Session(self._engine) as session:
      job = create_job(session, video_id)
      job_id = job.id
      update_job(session, job_id, JobStatus.RUNNING)

    print(f"  Ingesting: {title} ({video_id})")

    try:
      transcript = fetch_transcript(video_id)
      if not transcript:
        raise ValueError("No transcript available")

      if len(transcript.split()) < 50:
        raise ValueError(
          f"Transcript too short ({len(transcript.split())} words)"
        )

      import re
      raw_chunks = self._chunker.chunk_texts(transcript)
      if not raw_chunks:
        raise ValueError("Chunking produced no chunks")

      # Extract starting timestamps and clean the chunk text
      start_seconds = []
      clean_chunks = []
      for chunk_text in raw_chunks:
        match = re.search(r'\[t=(\d+)\]', chunk_text)
        start_sec = int(match.group(1)) if match else 0
        start_seconds.append(start_sec)
        
        # Clean all [t=seconds] markers from text so embeddings/search are pure
        clean_txt = re.sub(r'\[t=\d+\]', '', chunk_text).strip()
        clean_chunks.append(clean_txt)

      embeddings = self._embedder.embed(clean_chunks)

      with Session(self._engine) as session:
        from app.db.sqlite import select, Video
        video = session.exec(
          select(Video).where(Video.youtube_id == video_id)
        ).first()
        channel_name = "Unknown"
        if video:
          from app.db.sqlite import get_channel_by_youtube_id
          channel = get_channel_by_youtube_id(
            session, video.channel_youtube_id
          )
          if channel:
            channel_name = channel.name

      self._vectordb.upsert_chunks(
        chunks=clean_chunks,
        embeddings=embeddings,
        video_youtube_id=video_id,
        video_title=title,
        channel_name=channel_name,
        start_seconds=start_seconds,
      )

      with Session(self._engine) as session:
        from app.db.sqlite import insert_fts_chunk
        # Index each chunk incrementally into SQLite FTS5 virtual table
        for i, (txt, start_sec) in enumerate(zip(clean_chunks, start_seconds)):
          insert_fts_chunk(
            session=session,
            chunk_id=f"{video_id}_chunk_{i}",
            text_content=txt,
            video_youtube_id=video_id,
            video_title=title,
            channel_name=channel_name,
            chunk_index=i,
            start_second=start_sec,
          )

        mark_video_ingested(session, video_id, len(clean_chunks))
        update_job(session, job_id, JobStatus.DONE,
                  chunks_created=len(clean_chunks))

      print(f"[OK] {len(clean_chunks)} chunks stored")
      return True

    except Exception as e:
      print(f"[Failed] {e}")
      with Session(self._engine) as session:
        update_job(session, job_id, JobStatus.FAILED,
                  error_message=str(e))
      return False