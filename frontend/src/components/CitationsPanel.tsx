import React from "react";
import { Quote, Play } from "lucide-react";
import type { Citation, Source } from "../types";

interface CitationsPanelProps {
  citations: Citation[];
  sources: Source[];
}

export const CitationsPanel: React.FC<CitationsPanelProps> = ({ citations, sources }) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col gap-3 text-left">
      <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-500 flex items-center gap-2">
        <Quote className="h-3.5 w-3.5 text-violet-400" /> AI-Selected Quotes
      </h3>
      
      <div className="grid grid-cols-1 gap-4">
        {citations.map((cit, i) => {
          const matchingSource = sources.find(
            (src) => src.video_youtube_id === cit.video_id
          );
          const startSecond = matchingSource ? matchingSource.start_second : 0;
          const channelName = matchingSource ? matchingSource.channel_name : "Unknown Channel";
          const ytUrl = `https://youtube.com/watch?v=${cit.video_id}&t=${startSecond}s`;

          return (
            <div
              key={i}
              className="glass-card bg-slate-900/25 border border-slate-800/60 rounded-2xl p-5 flex flex-col justify-between group relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-1 h-full bg-violet-500/50 group-hover:bg-violet-400 transition-colors" />
              
              <div className="pl-2">
                <blockquote className="text-slate-200 italic text-sm md:text-base leading-relaxed border-l-2 border-slate-800 pl-4 py-1 mb-4">
                  "{cit.quote}"
                </blockquote>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-850/60 mt-2">
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold text-slate-300 leading-snug truncate max-w-70">
                      {cit.video_title}
                    </span>
                    <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">
                      {channelName}
                    </span>
                  </div>

                  <a
                    href={ytUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="self-start sm:self-center flex items-center gap-1.5 text-xs text-violet-400 group-hover:text-violet-300 font-bold bg-violet-500/5 hover:bg-violet-500/10 px-3.5 py-1.5 rounded-xl border border-violet-500/10 hover:border-violet-500/25 transition-all shadow-sm duration-300"
                  >
                    <Play className="h-3 w-3 fill-violet-400 group-hover:fill-violet-300" />
                    <span>Jump to timestamp ({formatTime(startSecond)})</span>
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
