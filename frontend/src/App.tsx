import { Sidebar } from "./components/Sidebar";
import { AskTab } from "./components/AskTab";
import { ChannelsTab } from "./components/ChannelsTab";
import { useRagState } from "./hooks/useRagState";

function App() {
  const {
    activeTab,
    setActiveTab,
    selectedChannel,
    setSelectedChannel,
    topK,
    setTopK,
    health,
    channels,
    fetchChannels,
    fetchHealth,
    apiUrl,
  } = useRagState();

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
            apiUrl={apiUrl}
          />
        ) : (
          <ChannelsTab
            channels={channels}
            fetchChannels={fetchChannels}
            fetchHealth={fetchHealth}
            apiUrl={apiUrl}
          />
        )}
      </main>
    </div>
  );
}

export default App;
