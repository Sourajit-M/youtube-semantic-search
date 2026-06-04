import React from "react";
import type { Channel } from "../types";
import { IngestConsole } from "./IngestConsole";
import { ChannelCard } from "./ChannelCard";

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
  const handleIngestSuccess = () => {
    fetchChannels();
    fetchHealth();
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
      <IngestConsole apiUrl={apiUrl} onIngestSuccess={handleIngestSuccess} />

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
            {channels.map((ch) => (
              <ChannelCard
                key={ch.youtube_id}
                ch={ch}
                apiUrl={apiUrl}
                onChannelDeleted={handleIngestSuccess}
                onHealthUpdate={fetchHealth}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
