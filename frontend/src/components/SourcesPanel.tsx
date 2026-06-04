import React from "react";
import { Layers, Play } from "lucide-react";
import type { Source } from "../types";

interface SourcesPanelProps {
  sources: Source[];
  maxRrf: number;
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({ sources, maxRrf }) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col gap-3 text-left">
      <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-500 flex items-center gap-2">
        <Layers className="h-3.5 w-3.5" /> Cited Source Material
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {sources.map((src, i) => {
          const ytUrl = `https://youtube.com/watch?v=${src.video_youtube_id}&t=${src.start_second}s`;
          const relevancePct = Math.round((src.rrf_score / maxRrf) * 100);

          // Phase 2: Color badge based on normalized relevance
          let badgeColors = "text-rose-400 bg-rose-500/10 border-rose-500/15";
          if (relevancePct >= 70) {
            badgeColors = "text-emerald-400 bg-emerald-500/10 border-emerald-500/15";
          } else if (relevancePct >= 40) {
            badgeColors = "text-amber-400 bg-amber-500/10 border-amber-500/15";
          }

          return (
            <div
              key={i}
              className="glass-card bg-slate-900/35 border border-slate-800/70 rounded-2xl p-4.5 flex flex-col justify-between group relative overflow-hidden"
            >
              <div className="flex justify-between items-start gap-4 mb-2.5">
                <a
                  href={ytUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-display font-bold text-slate-100 text-sm hover:text-violet-400 leading-snug line-clamp-2 transition-all"
                >
                  {src.video_title}
                </a>
                <span 
                  className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border shrink-0 shadow-sm transition-all duration-300 ${badgeColors}`} 
                  title={`Reciprocal Rank Fusion Score: ${src.rrf_score.toFixed(4)}`}
                >
                  Relevance {relevancePct}%
                </span>
              </div>

              <div className="flex items-center justify-between mt-auto pt-3 border-t border-slate-850/60">
                <span className="text-xs text-slate-500 font-semibold truncate max-w-42.5">
                  {src.channel_name}
                </span>

                <a
                  href={ytUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-violet-400 group-hover:text-violet-300 font-bold bg-violet-500/5 hover:bg-violet-500/10 px-3.5 py-1.5 rounded-xl border border-violet-500/10 hover:border-violet-500/25 transition-all shadow-sm duration-300"
                >
                  <Play className="h-3 w-3 fill-violet-400 group-hover:fill-violet-300" />
                  <span>At {formatTime(src.start_second)}</span>
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
