import React, { useState } from "react";
import { Plus, Search, Trash2, ChevronDown, ChevronUp, CheckCircle, Clock, Youtube, Eye, Calendar, RefreshCw, AlertTriangle, ArrowUpRight } from "lucide-react";

interface Channel {
  youtube_id: string;
  name: string;
  url: string;
  last_checked_at: string | null;
  created_at: string;
}

interface Video {
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

interface ChannelsTabProps {
  channels: Channel[];
  fetchChannels: () => void;
  fetchHealth: () => void;
  apiUrl: string;
}

export const ChannelsTab: React.FC<ChannelsTabProps> = ({
  channels,
  fetchChannels,
  fetchHealth,
  apiUrl,
}) => {
  // Ingest form
  const [channelInput, setChannelInput] = useState("");
  const [maxVideos, setMaxVideos] = useState(10);
  const [ingesting, setIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  // Deletion confirm track
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Expandable channels tracking
  const [expandedChannels, setExpandedChannels] = useState<Record<string, boolean>>({});
  const [channelVideos, setChannelVideos] = useState<Record<string, Video[]>>({});
  const [loadingVideos, setLoadingVideos] = useState<Record<string, boolean>>({});

  // Individual video index state
  const [indexingVideo, setIndexingVideo] = useState<string | null>(null);

  // Video search & status filter
  const [videoSearch, setVideoSearch] = useState<Record<string, string>>({});
  const [videoFilter, setVideoFilter] = useState<Record<string, "all" | "indexed" | "pending">>({});

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelInput.trim()) return;

    setIngesting(true);
    setIngestError(null);
    setIngestStatus("Connecting to YouTube ingestion engine...");

    try {
      const response = await fetch(`${apiUrl}/channels`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          channel_input: channelInput.trim(),
          max_videos: maxVideos,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setIngestStatus(`Successfully ingested ${data.videos_ingested} videos. (${data.videos_failed} failed)`);
      setChannelInput("");
      fetchChannels();
      fetchHealth();
    } catch (err: any) {
      console.error(err);
      setIngestError(err.message || "Ingestion pipeline failure. Check logs.");
    } finally {
      setIngesting(false);
    }
  };

  const handleDeleteChannel = async (youtubeId: string) => {
    setDeleting(youtubeId);
    try {
      const response = await fetch(`${apiUrl}/channels/${youtubeId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Failed to delete channel: ${response.status}`);
      }

      setDeleteConfirm(null);
      fetchChannels();
      fetchHealth();
    } catch (err: any) {
      alert(err.message || "Error deleting channel.");
    } finally {
      setDeleting(null);
    }
  };

  const fetchVideos = async (youtubeId: string) => {
    setLoadingVideos((prev) => ({ ...prev, [youtubeId]: true }));
    try {
      const response = await fetch(`${apiUrl}/channels/${youtubeId}/videos`);
      if (!response.ok) throw new Error("Could not retrieve videos");
      const data = await response.json();
      setChannelVideos((prev) => ({ ...prev, [youtubeId]: data }));
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingVideos((prev) => ({ ...prev, [youtubeId]: false }));
    }
  };

  const handleToggleChannel = (youtubeId: string) => {
    const isCurrentlyExpanded = !!expandedChannels[youtubeId];
    setExpandedChannels((prev) => ({ ...prev, [youtubeId]: !isCurrentlyExpanded }));
    
    // Load videos if expanding and not already loaded
    if (!isCurrentlyExpanded && !channelVideos[youtubeId]) {
      fetchVideos(youtubeId);
    }
  };

  const handleIndexVideo = async (youtubeId: string, channelYoutubeId: string) => {
    setIndexingVideo(youtubeId);
    try {
      const response = await fetch(`${apiUrl}/videos/${youtubeId}/ingest`, {
        method: "POST",
      });

      if (!response.ok) throw new Error("Video indexing failed.");
      
      // Reload this channel's videos & health stats
      fetchVideos(channelYoutubeId);
      fetchHealth();
    } catch (err: any) {
      alert(err.message || "Failed to index video.");
    } finally {
      setIndexingVideo(null);
    }
  };

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
    <div className="flex-1 h-full overflow-y-auto flex flex-col p-6 md:p-8 space-y-7 max-w-5xl mx-auto w-full">
      {/* Title */}
      <div className="flex flex-col gap-2">
        <h2 className="font-display font-extrabold text-2xl md:text-3xl bg-clip-text text-transparent bg-gradient-to-r from-slate-50 via-slate-100 to-indigo-200">
          Channel & Video Manager
        </h2>
        <p className="text-sm text-slate-400">
          Index new content or inspect indexed videos. Transcripts are segmented, processed via semantic models, and indexed dynamically.
        </p>
      </div>

      {/* Ingest terminal card */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 md:p-6 shadow-xl backdrop-blur-md">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
          <Youtube className="h-4 w-4 text-rose-500" /> Ingest From YouTube
        </h3>

        <form onSubmit={handleIngest} className="flex flex-col gap-4">
          <div className="flex flex-col md:flex-row gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={channelInput}
                disabled={ingesting}
                onChange={(e) => setChannelInput(e.target.value)}
                placeholder="YouTube Channel (@3blue1brown), URL or direct Video URL"
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-800 focus:border-violet-500/50 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:ring-1 focus:ring-violet-500/25 transition-all"
              />
            </div>
            
            <div className="w-full md:w-36 flex flex-col justify-center">
              <input
                type="number"
                min="0"
                max="200"
                disabled={ingesting}
                value={maxVideos}
                onChange={(e) => setMaxVideos(parseInt(e.target.value) || 0)}
                title="Max videos to scan on channel add (0 to scan ALL)"
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-800 focus:border-violet-500/50 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:ring-1 focus:ring-violet-500/25 text-center transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={ingesting || !channelInput.trim()}
              className="px-6 py-3 rounded-xl text-sm font-semibold shadow-lg shadow-violet-600/10 border border-violet-500/20 bg-gradient-to-r from-violet-600 to-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:from-violet-500 hover:to-indigo-400 cursor-pointer flex items-center justify-center gap-2 transition-all duration-300"
            >
              {ingesting ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  <span>Ingest Channel</span>
                </>
              )}
            </button>
          </div>

          <div className="flex flex-row justify-between text-[11px] font-medium text-slate-500 px-1">
            <span>Set video count to <strong className="text-slate-400">0</strong> to automatically index every video on the channel.</span>
            {maxVideos > 50 && (
              <span className="text-amber-400 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Scanning {maxVideos} videos can take up to ~{(maxVideos * 0.25).toFixed(1)} minutes.
              </span>
            )}
          </div>
        </form>

        {/* Progress or error feedback */}
        {(ingestStatus || ingestError) && (
          <div className={`mt-4 p-4 rounded-xl text-xs leading-relaxed border ${
            ingestError 
              ? "bg-rose-500/10 border-rose-500/20 text-rose-300" 
              : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
          }`}>
            <span className="font-bold block mb-1">
              {ingestError ? "Ingestion Pipeline Refused" : "Pipeline Command Acknowledged"}
            </span>
            {ingestError || ingestStatus}
          </div>
        )}
      </div>

      {/* Indexed Channels Section */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">
          Tracked Libraries ({channels.length})
        </h3>

        {channels.length === 0 ? (
          <div className="bg-slate-900/20 border border-slate-900 rounded-2xl p-8 text-center text-slate-500">
            No libraries tracked yet. Add one in the control console above.
          </div>
        ) : (
          <div className="space-y-3.5">
            {channels.map((ch) => {
              const videosList = channelVideos[ch.youtube_id] || [];
              const isExpanded = !!expandedChannels[ch.youtube_id];
              const videosLoading = !!loadingVideos[ch.youtube_id];
              
              const indexedCount = videosList.filter((v) => v.ingested).length;
              const pendingCount = videosList.filter((v) => !v.ingested).length;

              const searchVal = videoSearch[ch.youtube_id] || "";
              const activeFilter = videoFilter[ch.youtube_id] || "all";

              // Filter logic
              const filteredVideos = videosList.filter((v) => {
                const matchesSearch = v.title.toLowerCase().includes(searchVal.toLowerCase());
                if (activeFilter === "indexed") return matchesSearch && v.ingested;
                if (activeFilter === "pending") return matchesSearch && !v.ingested;
                return matchesSearch;
              });

              return (
                <div
                  key={ch.youtube_id}
                  className="bg-slate-900/40 border border-slate-850/80 rounded-2xl shadow-md transition-all overflow-hidden"
                >
                  {/* Channel Card Header */}
                  <div className="p-4 md:p-5 flex items-center justify-between flex-wrap md:flex-nowrap gap-4">
                    <div
                      onClick={() => handleToggleChannel(ch.youtube_id)}
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
                            disabled={deleting === ch.youtube_id}
                            onClick={() => handleDeleteChannel(ch.youtube_id)}
                            className="bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white font-bold text-[10px] px-2.5 py-1 rounded cursor-pointer transition-all uppercase tracking-wider"
                          >
                            {deleting === ch.youtube_id ? "Removing..." : "Delete"}
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
                      {videosLoading ? (
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
                                value={searchVal}
                                onChange={(e) => setVideoSearch((prev) => ({ ...prev, [ch.youtube_id]: e.target.value }))}
                                placeholder="Search channel videos..."
                                className="w-full bg-slate-950 border border-slate-850 focus:border-violet-500/40 rounded-xl pl-9.5 pr-4 py-2 text-xs text-slate-300 outline-none focus:ring-1 focus:ring-violet-500/20 transition-all"
                              />
                              <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                            </div>

                            <div className="flex items-center gap-1 bg-slate-950 border border-slate-850/85 p-0.5 rounded-lg shrink-0 w-full sm:w-auto overflow-hidden">
                              {(["all", "indexed", "pending"] as const).map((mode) => (
                                <button
                                  key={mode}
                                  onClick={() => setVideoFilter((prev) => ({ ...prev, [ch.youtube_id]: mode }))}
                                  className={`flex-1 sm:flex-initial px-3.5 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer ${
                                    activeFilter === mode
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
                              filteredVideos.map((video) => {
                                const videoUrl = `https://youtube.com/watch?v=${video.youtube_id}`;
                                return (
                                  <div
                                    key={video.youtube_id}
                                    className="p-3.5 flex items-center justify-between gap-4 hover:bg-slate-900/10 transition-colors"
                                  >
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
                                          disabled={indexingVideo === video.youtube_id}
                                          onClick={() => handleIndexVideo(video.youtube_id, ch.youtube_id)}
                                          className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-400 bg-violet-500/5 hover:bg-violet-500/10 px-3.5 py-1.5 rounded-xl border border-violet-500/10 hover:border-violet-500/25 cursor-pointer disabled:opacity-40 transition-all duration-300"
                                        >
                                          {indexingVideo === video.youtube_id ? (
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
                              })
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
