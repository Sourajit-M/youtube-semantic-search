import React from "react";
import { MessageSquare, Tv, Activity, Database, Cpu, Compass, Layers, Sliders } from "lucide-react";

interface Channel {
  youtube_id: string;
  name: string;
  url: string;
  last_checked_at: string | null;
  created_at: string;
}

interface Health {
  status: string;
  chunks_indexed: number;
  channels_tracked: number;
  active_llm: string;
}

interface SidebarProps {
  activeTab: "ask" | "channels";
  setActiveTab: (tab: "ask" | "channels") => void;
  selectedChannel: string;
  setSelectedChannel: (channel: string) => void;
  topK: number;
  setTopK: (k: number) => void;
  health: Health | null;
  channels: Channel[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  selectedChannel,
  setSelectedChannel,
  topK,
  setTopK,
  health,
  channels,
}) => {
  return (
    <aside className="w-80 h-full glass-panel flex flex-col border-r border-slate-800/60 p-6 select-none shrink-0 overflow-y-auto">
      {/* Header / Logo */}
      <div className="flex items-center gap-3 mb-8">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
          <Tv className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="font-display font-bold text-lg leading-tight tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-300">
            YouTube RAG
          </h1>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-violet-400">
            Control Console
          </span>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex flex-col gap-2.5 mb-8">
        <button
          onClick={() => setActiveTab("ask")}
          className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === "ask"
              ? "bg-gradient-to-r from-violet-600/90 to-indigo-500/90 text-white shadow-lg shadow-violet-600/25 border border-violet-500/30"
              : "text-slate-400 hover:text-white hover:bg-slate-800/40 border border-transparent"
          }`}
        >
          <MessageSquare className="h-4.5 w-4.5" />
          <span>Ask AI Assistant</span>
        </button>

        <button
          onClick={() => setActiveTab("channels")}
          className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === "channels"
              ? "bg-gradient-to-r from-violet-600/90 to-indigo-500/90 text-white shadow-lg shadow-violet-600/25 border border-violet-500/30"
              : "text-slate-400 hover:text-white hover:bg-slate-800/40 border border-transparent"
          }`}
        >
          <Tv className="h-4.5 w-4.5" />
          <span>Ingest & Channels</span>
        </button>
      </div>

      {/* Live System stats */}
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

      <hr className="border-slate-800/50 mb-6" />

      {/* Query Filters */}
      <div className="flex flex-col gap-5.5 mt-auto">
        <div>
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-3">
            <Compass className="h-3 w-3" /> Context Scope
          </h3>
          <div className="relative">
            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all appearance-none cursor-pointer"
            >
              <option value="All channels">All Indexed Channels</option>
              {channels.map((ch) => (
                <option key={ch.youtube_id} value={ch.name}>
                  {ch.name}
                </option>
              ))}
            </select>
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500 border-l border-slate-800/80 pl-2">
              <Layers className="h-3.5 w-3.5" />
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Sliders className="h-3 w-3" /> Retrieve Depth
            </h3>
            <span className="text-xs font-mono font-bold text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded border border-violet-500/15">
              {topK} Chunks
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold text-slate-600">1</span>
            <input
              type="range"
              min="1"
              max="15"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-500 hover:accent-violet-400 focus:outline-none"
            />
            <span className="text-[10px] font-bold text-slate-600">15</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
