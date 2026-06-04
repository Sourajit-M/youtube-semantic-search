import React, { useState } from "react";
import { ChevronDown, ChevronUp, CheckCircle, Clock, Trash2, Search, RefreshCw } from "lucide-react";
import type { Channel, Video } from "../types";
import { VideoRow } from "./VideoRow";

interface ChannelCardProps {
  ch: Channel;
  apiUrl: string;
  onChannelDeleted: () => void;
  onHealthUpdate: () => void;
}

export const ChannelCard: React.FC<ChannelCardProps> = ({
  ch,
  apiUrl,
  onChannelDeleted,
  onHealthUpdate,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  
  // Deletion confirm tracking
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Individual video index state
  const [indexingVideo, setIndexingVideo] = useState<string | null>(null);

  // Video search & status filter
  const [videoSearch, setVideoSearch] = useState("");
  const [videoFilter, setVideoFilter] = useState<"all" | "indexed" | "pending">("all");

  const fetchVideos = async () => {
    setLoadingVideos(true);
    try {
      const response = await fetch(`${apiUrl}/channels/${ch.youtube_id}/videos`);
      if (!response.ok) throw new Error("Could not retrieve videos");
      const data = await response.json();
      setVideos(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingVideos(false);
    }
  };

  const handleToggle = () => {
    const nextState = !isExpanded;
    setIsExpanded(nextState);
    if (nextState && videos.length === 0) {
      fetchVideos();
    }
  };

  const handleDeleteChannel = async () => {
    setDeleting(true);
    try {
      const response = await fetch(`${apiUrl}/channels/${ch.youtube_id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Failed to delete channel: ${response.status}`);
      }

      setDeleteConfirm(null);
      onChannelDeleted();
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Error deleting channel.";
      alert(errMsg);
    } finally {
      setDeleting(false);
    }
  };

  const handleIndexVideo = async (youtubeId: string) => {
    setIndexingVideo(youtubeId);
    try {
      const response = await fetch(`${apiUrl}/videos/${youtubeId}/ingest`, {
        method: "POST",
      });

      if (!response.ok) throw new Error("Video indexing failed.");
      
      // Reload this channel's videos & health stats
      fetchVideos();
      onHealthUpdate();
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Failed to index video.";
      alert(errMsg);
    } finally {
      setIndexingVideo(null);
    }
  };

  const indexedCount = videos.filter((v) => v.ingested).length;
  const pendingCount = videos.filter((v) => !v.ingested).length;

  // Filter logic
  const filteredVideos = videos.filter((v) => {
    const matchesSearch = v.title.toLowerCase().includes(videoSearch.toLowerCase());
    if (videoFilter === "indexed") return matchesSearch && v.ingested;
    if (videoFilter === "pending") return matchesSearch && !v.ingested;
    return matchesSearch;
  });

  return (
    <div className="bg-slate-900/40 border border-slate-850/80 rounded-2xl shadow-md transition-all overflow-hidden">
      {/* Channel Card Header */}
      <div className="p-4 md:p-5 flex items-center justify-between flex-wrap md:flex-nowrap gap-4">
        <div
          onClick={handleToggle}
          className="flex-1 flex items-start gap-3 cursor-pointer select-none group"
        >
          <div className="h-10 w-10 rounded-xl bg-slate-950 flex items-center justify-center border border-slate-800 text-slate-400 group-hover:border-violet-500/30 group-hover:text-violet-400 transition-all duration-300">
            {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </div>
          <div className="space-y-1">
            <h4 className="font-display font-extrabold text-slate-200 text-base flex items-center gap-2 group-hover:text-violet-400 transition-all">
              {ch.name}
            </h4>
            <div className="flex items-center gap-3 text-xs text-slate-500 font-medium">
              <span className="truncate max-w-[180px] md:max-w-xs">{ch.url}</span>
              <span>•</span>
              <span>Last Checked: {ch.last_checked_at ? ch.last_checked_at.slice(0, 10) : "never"}</span>
            </div>
          </div>
        </div>

        {/* Stats pills & Delete button */}
        <div className="flex items-center gap-3 ml-auto shrink-0">
          <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/15 shadow-sm">
            <CheckCircle className="h-3 w-3" />
            <span>{ch.last_checked_at ? indexedCount : "—"} Indexed</span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/15 shadow-sm">
            <Clock className="h-3 w-3" />
            <span>{ch.last_checked_at ? pendingCount : "—"} Pending</span>
          </div>

          <div className="border-l border-slate-800 h-6.5 mx-1" />

          {/* 2-step delete */}
          {deleteConfirm === ch.youtube_id ? (
            <div className="flex items-center gap-1 bg-rose-500/10 p-0.5 rounded-lg border border-rose-500/20">
              <button
                disabled={deleting}
                onClick={handleDeleteChannel}
                className="bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white font-bold text-[10px] px-2.5 py-1 rounded cursor-pointer transition-all uppercase tracking-wider"
              >
                {deleting ? "Removing..." : "Delete"}
              </button>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="text-slate-400 hover:text-white text-[10px] font-bold px-2 py-1 cursor-pointer transition-all"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setDeleteConfirm(ch.youtube_id)}
              title="Unregister Channel & Delete Index"
              className="h-9 w-9 rounded-xl bg-slate-950 hover:bg-rose-500/15 text-slate-500 hover:text-rose-400 border border-slate-850 hover:border-rose-500/20 flex items-center justify-center cursor-pointer transition-all duration-300"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Expandable Drawers Panel */}
      {isExpanded && (
        <div className="border-t border-slate-850/80 bg-slate-950/20 p-4.5 space-y-4">
          {loadingVideos ? (
            <div className="flex items-center justify-center py-6 gap-2.5 text-sm text-slate-500">
              <RefreshCw className="h-4 w-4 animate-spin text-violet-400" />
              <span>Polling video database...</span>
            </div>
          ) : (
            <>
              {/* Search / Filter header */}
              <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
                <div className="relative w-full sm:max-w-xs">
                  <input
                    type="text"
                    value={videoSearch}
                    onChange={(e) => setVideoSearch(e.target.value)}
                    placeholder="Search channel videos..."
                    className="w-full bg-slate-950 border border-slate-850 focus:border-violet-500/40 rounded-xl pl-9.5 pr-4 py-2 text-xs text-slate-300 outline-none focus:ring-1 focus:ring-violet-500/20 transition-all"
                  />
                  <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>

                <div className="flex items-center gap-1 bg-slate-950 border border-slate-850/85 p-0.5 rounded-lg shrink-0 w-full sm:w-auto overflow-hidden">
                  {(["all", "indexed", "pending"] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setVideoFilter(mode)}
                      className={`flex-1 sm:flex-initial px-3.5 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer ${
                        videoFilter === mode
                          ? "bg-slate-900 text-violet-400 shadow-sm border border-slate-850"
                          : "text-slate-500 hover:text-slate-300 border border-transparent"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              {/* List of videos */}
              <div className="border border-slate-900 rounded-xl overflow-hidden divide-y divide-slate-900 max-h-80 overflow-y-auto">
                {filteredVideos.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 font-medium">
                    No matching videos found in index.
                  </div>
                ) : (
                  filteredVideos.map((video) => (
                    <VideoRow
                      key={video.youtube_id}
                      video={video}
                      isIndexing={indexingVideo === video.youtube_id}
                      onIndexVideo={handleIndexVideo}
                    />
                  ))
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
