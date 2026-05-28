from typing import Optional
from pydantic import BaseModel, Field

class AddChannelRequest(BaseModel):
  channel_input: str = Field(
    description="Channel handle (@crashcourse), URL, or ID",
    examples=["@crashcourse", "https://www.youtube.com/@crashcourse"]
  )
  max_videos: int = Field(
    default=50,
    ge=0,
    le=500,
    description="Max videos to ingest on first add"
  )

class AskRequest(BaseModel):
  question: str = Field(
    min_length=3,
    description="Natural language question is answer from video content"
  )

  channel_name: Optional[str] = Field(
    default=None,
    description="Restrict search to this channel name"
  )

  top_k: int = Field(default=5, ge=1, le=20)


class SearchRequest(BaseModel):
  query: str = Field(min_length=2)
  channel_name: Optional[str] = None
  top_k: int = Field(default=5, ge=1, le=20)


class SourceVideo(BaseModel):
  video_youtube_id: str
  video_title: str
  channel_name: str
  rrf_score: float
  start_second: int = 0


class AskResponse(BaseModel):
  answer: str
  sources: list[SourceVideo]
  chunks_used: int
  provider: str

class SearchResult(BaseModel):
  chunk_id: str
  video_youtube_id: str
  video_title: str
  channel_name: str
  text: str
  rrf_score: float
  chunk_index: int
  start_second: int = 0


class SearchResponse(BaseModel):
  results: list[SearchResult]
  total: int

class ChannelResponse(BaseModel):
  youtube_id: str
  name: str
  url: str
  last_checked_at: Optional[str]
  created_at: str


class AddChannelResponse(BaseModel):
  channel_id: str
  channel_name: str
  videos_found: int
  videos_ingested: int
  videos_failed: int
  message: str


class VideoResponse(BaseModel):
  youtube_id: str
  title: str
  description: Optional[str]
  published_at: Optional[str]
  duration_seconds: Optional[int]
  view_count: Optional[int]
  like_count: Optional[int]
  thumbnail_url: Optional[str]
  ingested: bool
  ingested_at: Optional[str]


class HealthResponse(BaseModel):
  status: str
  chunks_indexed: int
  channels_tracked: int
  active_llm: str