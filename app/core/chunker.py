import re
from dataclasses import dataclass

from app.config import get_settings

@dataclass
class Chunk:
  text: str 
  chunk_index: int 
  start_token: int
  end_token: int

class TranscriptChunker:
  def __init__(self):
    settings = get_settings()
    self.chunk_size = settings.chunk_size
    self.overlap = settings.chunk_overlap
    self.step = self.chunk_size - self.overlap

  def clean(self, text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    # Strip generic bracket annotations (like [Music]) but preserve our custom time markers ([t=XX])
    text = re.sub(r'\[(?!t=\d+\])[^\]]*\]', '', text)

    return text.strip()

  def chunk(self, transcript: str) -> list[Chunk]:
    cleaned = self.clean(transcript)
    if not cleaned:
      return []

    words = cleaned.split()
    if len(words) < 30:
      # Transcript too short to chunk — return as single chunk
      return [Chunk(
        text=cleaned, 
        chunk_index=0,
        start_token=0,
        end_token=len(words)
      )]

    chunks = []
    start = 0
    index = 0

    while start < len(words):
      end = min(start + self.chunk_size, len(words))
      window_words = words[start:end]

      # Skip chunks that are too short — last window is often a few words
      if len(window_words) >= 30:
        chunks.append(Chunk(
          text=' '.join(window_words),
          chunk_index=index,
          start_token=start,
          end_token=end,
        ))
        index += 1
      
      # reached the end of the transcript, stop
      if end == len(words):
        break

      start += self.step

    return chunks
  
  def chunk_texts(self, transcript: str) -> list[str]:
    return [chunk.text for chunk in self.chunk(transcript)]