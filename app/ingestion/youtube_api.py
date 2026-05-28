import re 
from datetime import datetime
from typing import Optional

from googleapiclient.discovery import build

from app.config import get_settings

#youtube api client
def get_youtube_client():
  settings = get_settings()
  return build("youtube", "v3", developerKey=settings.youtube_api_key)


#channel resolution
def extract_video_id(video_input: str) -> Optional[str]:
  """
  Extracts the YouTube video ID from a URL or raw ID.
  Handles watch URLs, youtu.be, and embed URLs.
  """
  video_input = video_input.strip()

  # Regular expression for various YouTube URL formats
  patterns = [
    r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
    r'youtu\.be\/([0-9A-Za-z_-]{11})',
  ]

  for pattern in patterns:
    match = re.search(pattern, video_input)
    if match:
      return match.group(1)

  # Check if the input is a raw 11-char ID
  if re.match(r'^[0-9A-Za-z_-]{11}$', video_input):
    return video_input

  return None

def fetch_video_details_by_id(video_id: str) -> dict:
  """Fetch full details for a single video including channelId."""
  youtube = get_youtube_client()
  response = youtube.videos().list(
    part="snippet,contentDetails,statistics",
    id=video_id
  ).execute()

  if not response.get("items"):
    raise ValueError(f"Video not found: {video_id}")

  return _parse_video(response["items"][0])

def fetch_channel_info(channel_id: str) -> dict:
  """Fetch basic channel info (name)."""
  youtube = get_youtube_client()
  response = youtube.channels().list(
    part="snippet",
    id=channel_id
  ).execute()

  if not response.get("items"):
    raise ValueError(f"Channel not found: {channel_id}")

  item = response["items"][0]
  return {
    "id": item["id"],
    "title": item["snippet"]["title"]
  }

def resolve_channel_id(channel_input: str) -> tuple[str, str]:
  youtube = get_youtube_client()

  channel_input = channel_input.strip()
  for prefix in [
    "https://www.youtube.com/",
    "http://www.youtube.com/",
    "https://youtube.com/",
    "http://youtube.com/",
  ]:
    channel_input = channel_input.removeprefix(prefix)

  for prefix in [
    "channel/",
    "c/",
    "user/",
  ]:
    channel_input = channel_input.removeprefix(prefix)

  # Strip trailing slash and common tab suffixes
  channel_input = channel_input.rstrip('/')
  for suffix in [
    "/videos",
    "/featured",
    "/playlists",
    "/shorts",
    "/streams",
    "/community",
  ]:
    channel_input = channel_input.removesuffix(suffix)
  channel_input = channel_input.rstrip('/')

  if re.match(r'^UC[\w-]{22}$', channel_input):
    response = youtube.channels().list(
      part="snippet", id=channel_input
    ).execute()
    if response["items"]:
      return channel_input, response["items"][0]["snippet"]["title"]
    raise ValueError(f"Channel ID not found: {channel_input}")

  handle = channel_input.lstrip('@')
  response = youtube.channels().list(
    part = "snippet", forHandle=handle
  ).execute()
  
  if response.get("items"):
    item = response["items"][0]
    return item["id"], item["snippet"]["title"]

  raise ValueError(
    f"Could not resolve channel: {channel_input}. "
    "Try the full channel URL from your browser."
  )

#video metadata
def fetch_channel_videos(
  channel_id: str,
  max_results: int = 50
) -> list[dict]:
  youtube = get_youtube_client()

  channel_response = youtube.channels().list(
    part="contentDetails,snippet",
    id=channel_id,
  ).execute()

  if not channel_response["items"]:
    raise ValueError(f"Channel not found: {channel_id}")

  channel_info = channel_response["items"][0]
  uploads_playlist_id = (
    channel_info["contentDetails"]["relatedPlaylists"]["uploads"]
  )


  videos = []
  next_page_token = None

  while True:
    playlist_response = youtube.playlistItems().list(
      part="snippet,contentDetails",
      playlistId=uploads_playlist_id,
      maxResults=min(50, max_results - len(videos)) if max_results else 50,
      pageToken=next_page_token,
    ).execute()

    video_ids = [
      item["contentDetails"]["videoId"]
      for item in playlist_response["items"]
    ]

    details_response = youtube.videos().list(
      part="snippet,contentDetails,statistics",
      id=",".join(video_ids),
    ).execute()

    for item in details_response["items"]:
      videos.append(_parse_video(item))

    next_page_token = playlist_response.get("nextPageToken")

    if not next_page_token:
      break
    if max_results and len(videos) >= max_results:
      break

  return videos[:max_results] if max_results else videos


def _parse_video(item: dict) -> dict:
  snippet = item.get("snippet", {})
  stats = item.get("statistics", {})
  content = item.get("contentDetails", {})

  return {
    "youtube_id": item["id"],
    "channel_id": snippet.get("channelId"),
    "title": snippet.get("title", ""),
    "description": snippet.get("description", "")[:500],
    "published_at": _parse_iso_datetime(snippet.get("publishedAt")),
    "thumbnail_url": (
      snippet.get("thumbnails", {})
      .get("high", {})
      .get("url")
    ),
    "duration_seconds": _parse_duration(content.get("duration", "")),
    "view_count": int(stats.get("viewCount", 0)),
    "like_count": int(stats.get("likeCount", 0)),
  }

def _parse_duration(iso_duration: str) -> int:
  if not iso_duration:
    return 0

  pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
  match = re.match(pattern, iso_duration)

  if not match:
    return 0

  hours = int(match.group(1) or 0)
  minutes = int(match.group(2) or 0)
  seconds = int(match.group(3) or 0)

  return hours * 3600 + minutes * 60 + seconds


def _parse_iso_datetime(iso_str: Optional[str]) -> Optional[datetime]:
  if not iso_str:
    return None
  try:
    # YouTube uses Z for UTC, which fromisoformat handles in Python 3.11+
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
  except Exception:
    return None