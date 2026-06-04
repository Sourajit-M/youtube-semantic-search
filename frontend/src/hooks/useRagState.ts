import { useState, useEffect } from "react";
import type { Channel, Health } from "../types";

export const API_URL = import.meta.env.VITE_API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://localhost:8000" : "");

export const useRagState = () => {
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
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchChannels();
    }
  }, [activeTab]);

  return {
    activeTab,
    setActiveTab,
    selectedChannel,
    setSelectedChannel,
    topK,
    setTopK,
    health,
    channels,
    fetchHealth,
    fetchChannels,
    apiUrl: API_URL,
  };
};
