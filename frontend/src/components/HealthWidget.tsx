import React from "react";
import { Activity, Database, Tv, Cpu } from "lucide-react";
import type { Health } from "../types";

interface HealthWidgetProps {
  health: Health | null;
}

export const HealthWidget: React.FC<HealthWidgetProps> = ({ health }) => {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3.5">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <Activity className="h-3 w-3" /> System Health
        </h3>
        {health ? (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Online
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-xs text-rose-400 font-semibold bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
            Offline
          </span>
        )}
      </div>

      {health ? (
        <div className="grid grid-cols-2 gap-2.5">
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 flex flex-col">
            <span className="text-[10px] font-medium text-slate-500 flex items-center gap-1 mb-1">
              <Database className="h-3 w-3 text-violet-400" /> Chunks
            </span>
            <span className="font-display font-bold text-lg text-slate-100">
              {health.chunks_indexed.toLocaleString()}
            </span>
          </div>
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 flex flex-col">
            <span className="text-[10px] font-medium text-slate-500 flex items-center gap-1 mb-1">
              <Tv className="h-3 w-3 text-indigo-400" /> Channels
            </span>
            <span className="font-display font-bold text-lg text-slate-100">
              {health.channels_tracked}
            </span>
          </div>
          <div className="col-span-2 bg-slate-900/60 border border-slate-800/80 rounded-xl px-3.5 py-2.5 flex items-center justify-between gap-2.5">
            <span className="text-[10px] font-medium text-slate-500 flex items-center gap-1">
              <Cpu className="h-3.5 w-3.5 text-fuchsia-400" /> Active LLM
            </span>
            <span className="text-xs font-mono font-bold text-violet-300 truncate max-w-[140px]" title={health.active_llm}>
              {health.active_llm.split("/").pop()}
            </span>
          </div>
        </div>
      ) : (
        <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3.5 text-center text-xs text-rose-300/80 leading-relaxed font-medium">
          Run backend with: <br />
          <code className="text-rose-400 font-mono text-[10px] mt-1.5 block bg-rose-950/40 p-1.5 rounded border border-rose-500/15">
            uvicorn app.api.main:app --reload
          </code>
        </div>
      )}
    </div>
  );
};
