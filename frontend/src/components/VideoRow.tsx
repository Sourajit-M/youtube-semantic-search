import React from "react";
import { Eye, Calendar, RefreshCw, ArrowUpRight } from "lucide-react";
import type { Video } from "../types";

interface VideoRowProps {
  video: Video;
  isIndexing: boolean;
  onIndexVideo: (youtubeId: string) => void;
}

export const VideoRow: React.FC<VideoRowProps> = ({ video, isIndexing, onIndexVideo }) => {
  const videoUrl = `https://youtube.com/watch?v=${video.youtube_id}`;

  const formatViews = (views: number | null) => {
    if (views === null) return "0";
    if (views >= 1_000_000) return `${(views / 1_000_000).toFixed(1)}M`;
    if (views >= 1_000) return `${Math.round(views / 1_000)}K`;
    return views.toString();
  };

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return "";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="p-3.5 flex items-center justify-between gap-4 hover:bg-slate-900/10 transition-colors">
      <div className="flex-1 min-w-0 flex items-center gap-2.5">
        <span className={`shrink-0 h-2 w-2 rounded-full ${
          video.ingested ? "bg-emerald-500 shadow-sm shadow-emerald-500/30" : "bg-amber-500 shadow-sm shadow-amber-500/30"
        }`} title={video.ingested ? "Grounded in index" : "Ingest Pending"} />
        
        <div className="min-w-0 space-y-0.5">
          <a
            href={videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold text-slate-300 hover:text-violet-400 truncate block font-sans"
          >
            {video.title}
          </a>
          <div className="flex items-center gap-2.5 text-[10px] text-slate-500 font-semibold font-mono">
            {video.duration_seconds && (
              <span>Duration: {formatDuration(video.duration_seconds)}</span>
            )}
            {video.view_count !== null && (
              <span className="flex items-center gap-1">
                <Eye className="h-3 w-3 text-slate-650" />
                {formatViews(video.view_count)} views
              </span>
            )}
            {video.published_at && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3 text-slate-650" />
                {video.published_at.slice(0, 10)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Action button */}
      <div className="shrink-0">
        {video.ingested ? (
          <span className="text-[10px] font-bold text-slate-500 bg-slate-950 px-3.5 py-1.5 rounded-xl border border-slate-900 cursor-default">
            ✓ Ready
          </span>
        ) : (
          <button
            disabled={isIndexing}
            onClick={() => onIndexVideo(video.youtube_id)}
            className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-400 bg-violet-500/5 hover:bg-violet-500/10 px-3.5 py-1.5 rounded-xl border border-violet-500/10 hover:border-violet-500/25 cursor-pointer disabled:opacity-40 transition-all duration-300"
          >
            {isIndexing ? (
              <>
                <RefreshCw className="h-3 w-3 animate-spin" />
                <span>Indexing...</span>
              </>
            ) : (
              <>
                <ArrowUpRight className="h-3 w-3" />
                <span>Index Now</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
