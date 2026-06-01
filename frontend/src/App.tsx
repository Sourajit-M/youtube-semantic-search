import { useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { AskTab } from "./components/AskTab";
import { ChannelsTab } from "./components/ChannelsTab";

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

const API_URL = import.meta.env.VITE_API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://localhost:8000" : "");

function App() {
  const [activeTab, setActiveTab] = useState<"ask" | "channels">("ask");
  const [selectedChannel, setSelectedChannel] = useState<string>("All channels");
  const [topK, setTopK] = useState<number>(5);
  const [health, setHealth] = useState<Health | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);

  const fetchHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/health`, { method: "GET" });
      if (!response.ok) throw new Error("Health check failure");
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      console.warn("Backend offline:", err);
      setHealth(null);
    }
  };

  const fetchChannels = async () => {
    try {
      const response = await fetch(`${API_URL}/channels`, { method: "GET" });
      if (!response.ok) throw new Error("Failed to load channel lists");
      const data = await response.json();
      setChannels(data);
    } catch (err) {
      console.warn("Could not retrieve channel registries:", err);
      setChannels([]);
    }
  };

  // Run initial polling & tickers setup
  useEffect(() => {
    fetchHealth();
    fetchChannels();

    const ticker = setInterval(() => {
      fetchHealth();
    }, 15000); // Poll health every 15s

    return () => clearInterval(ticker);
  }, []);

  // Fetch channels when tab changes to ensure active synchronization
  useEffect(() => {
    if (activeTab === "channels") {
      fetchChannels();
    }
  }, [activeTab]);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex overflow-hidden font-sans select-none antialiased">
      {/* Sidebar navigation & filters panel */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedChannel={selectedChannel}
        setSelectedChannel={setSelectedChannel}
        topK={topK}
        setTopK={setTopK}
        health={health}
        channels={channels}
      />

      {/* Main dashboard tab context */}
      <main className="flex-1 h-full overflow-hidden bg-slate-950/20 flex flex-col relative">
        {/* Soft background light beams */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-violet-600/5 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-indigo-600/5 rounded-full blur-[100px] pointer-events-none" />

        {activeTab === "ask" ? (
          <AskTab
            selectedChannel={selectedChannel}
            topK={topK}
            apiUrl={API_URL}
          />
        ) : (
          <ChannelsTab
            channels={channels}
            fetchChannels={fetchChannels}
            fetchHealth={fetchHealth}
            apiUrl={API_URL}
          />
        )}
      </main>
    </div>
  );
}

export default App;
