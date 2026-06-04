export interface Source {
  video_youtube_id: string;
  video_title: string;
  channel_name: string;
  rrf_score: number;
  start_second: number;
}

export interface Citation {
  video_id: string;
  video_title: string;
  quote: string;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  citations: Citation[];
  chunks_used: number;
  provider: string;
}

export interface Channel {
  youtube_id: string;
  name: string;
  url: string;
  last_checked_at: string | null;
  created_at: string;
}

export interface Video {
  youtube_id: string;
  title: string;
  description: string | null;
  published_at: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  like_count: number | null;
  thumbnail_url: string | null;
  ingested: boolean;
  ingested_at: string | null;
}

export interface Health {
  status: string;
  chunks_indexed: number;
  channels_tracked: number;
  active_llm: string;
}
