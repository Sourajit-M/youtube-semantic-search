import React, { useState } from "react";
import { Plus, Youtube, RefreshCw, AlertTriangle } from "lucide-react";

interface IngestConsoleProps {
  apiUrl: string;
  onIngestSuccess: () => void;
}

export const IngestConsole: React.FC<IngestConsoleProps> = ({ apiUrl, onIngestSuccess }) => {
  const [channelInput, setChannelInput] = useState("");
  const [maxVideos, setMaxVideos] = useState(10);
  const [ingesting, setIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

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
      onIngestSuccess();
    } catch (err) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : "Ingestion pipeline failure. Check logs.";
      setIngestError(errMsg);
    } finally {
      setIngesting(false);
    }
  };

  return (
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
  );
};
