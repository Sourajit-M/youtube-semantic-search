import React, { useState } from "react";
import { Send, Sparkles, MessageSquare, AlertCircle, FileText, Cpu, Compass, Play, Layers } from "lucide-react";

interface Source {
  video_youtube_id: string;
  video_title: string;
  channel_name: string;
  rrf_score: number;
  start_second: number;
}

interface AskResponse {
  answer: string;
  sources: Source[];
  chunks_used: number;
  provider: string;
}

interface AskTabProps {
  selectedChannel: string;
  topK: number;
  apiUrl: string;
}

const EXAMPLES = [
  "What is LLM?",
  "What is meant by Hallucinations in LLM?",
  "How AI work?",
];

export const AskTab: React.FC<AskTabProps> = ({ selectedChannel, topK, apiUrl }) => {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload: Record<string, any> = {
        question: queryText.trim(),
        top_k: topK,
      };

      if (selectedChannel && selectedChannel !== "All channels") {
        payload.channel_name = selectedChannel;
      }

      const response = await fetch(`${apiUrl}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred connecting to the RAG endpoint.");
    } finally {
      setLoading(false);
    }
  };

  const formatAnswer = (text: string) => {
    // Simple formatter for paragraphs and basic bold text
    return text.split("\n\n").map((para, i) => {
      // Replace **text** with strong tags
      const formatted = para.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      return (
        <p
          key={i}
          className="mb-4 text-slate-200 leading-relaxed text-sm md:text-base font-normal last:mb-0"
          dangerouslySetInnerHTML={{ __html: formatted }}
        />
      );
    });
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex-1 h-full overflow-y-auto flex flex-col p-6 md:p-8 space-y-6 max-w-5xl mx-auto w-full">
      {/* Title block */}
      <div className="flex flex-col gap-2">
        <h2 className="font-display font-extrabold text-2xl md:text-3xl bg-clip-text text-transparent bg-gradient-to-r from-slate-50 via-slate-100 to-indigo-200">
          Ask YouTube AI
        </h2>
        <p className="text-sm text-slate-400">
          Ask questions grounded in the video transcripts. Our pipeline synthesizes answers with citations directly from indexed content.
        </p>
      </div>

      {/* Suggested chips */}
      <div className="flex flex-col gap-2.5">
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-violet-400" /> Click to Quick Ask
        </span>
        <div className="flex flex-wrap gap-2.5">
          {EXAMPLES.map((ex, idx) => (
            <button
              key={idx}
              disabled={loading}
              onClick={() => {
                setQuestion(ex);
                handleAsk(ex);
              }}
              className="text-xs text-slate-300 bg-slate-900/60 border border-slate-800/80 rounded-xl px-4 py-2.5 hover:bg-violet-900/10 hover:border-violet-500/30 active:scale-97 hover:text-violet-300 font-medium transition-all cursor-pointer duration-200"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Console Prompter input */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4 flex flex-col gap-3.5 shadow-xl backdrop-blur-md">
        <textarea
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your prompt here... (e.g. How do scientists study Earth's interior?)"
          className="bg-transparent border-0 text-slate-100 placeholder-slate-500 w-full outline-none resize-none text-sm md:text-base leading-relaxed"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAsk(question);
            }
          }}
        />
        <div className="flex justify-between items-center pt-2.5 border-t border-slate-800/50">
          <span className="text-[10px] text-slate-500 font-mono">
            Press <kbd className="bg-slate-800 px-1 py-0.5 rounded text-[9px] font-sans border border-slate-700">Enter</kbd> to ask
          </span>
          <button
            onClick={() => handleAsk(question)}
            disabled={loading || !question.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold shadow-lg shadow-violet-600/15 border border-violet-500/20 bg-gradient-to-r from-violet-600 to-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:from-violet-500 hover:to-indigo-400 active:scale-97 cursor-pointer transition-all duration-300"
          >
            {loading ? (
              <>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-white typing-dot" />
                  <span className="h-1.5 w-1.5 rounded-full bg-white typing-dot" />
                  <span className="h-1.5 w-1.5 rounded-full bg-white typing-dot" />
                </div>
                <span>Synthesizing...</span>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Ask AI</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-start gap-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 p-4.5 rounded-2xl animate-fade-in">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
          <div className="text-sm leading-relaxed">
            <span className="font-bold block mb-0.5">Pipeline Query Error</span>
            {error}
          </div>
        </div>
      )}

      {/* Synthesizing / Loader UI */}
      {loading && (
        <div className="bg-slate-900/40 border border-slate-850 rounded-2xl p-6 flex flex-col items-center justify-center space-y-4 animate-pulse">
          <div className="relative h-12 w-12 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-2 border-t-violet-500 border-r-transparent border-slate-800 animate-spin" />
            <Sparkles className="h-5 w-5 text-violet-400" />
          </div>
          <div className="text-center space-y-1">
            <h4 className="text-sm font-semibold text-slate-200">Retrieving & Reranking</h4>
            <p className="text-xs text-slate-400">Searching transcripts & grounding with LLM parameters...</p>
          </div>
        </div>
      )}

      {/* Answer Console Block */}
      {result && (
        <div className="flex flex-col gap-6 animate-fade-in">
          {/* Main Answer card */}
          <div className="glass-panel border-slate-800/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-violet-600 to-indigo-500" />
            
            {/* Header info */}
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className="h-4.5 w-4.5 text-violet-400" />
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Grounded Synthesis</span>
            </div>

            {/* Answer text */}
            <div className="text-slate-100 leading-relaxed font-sans">
              {formatAnswer(result.answer)}
            </div>

            {/* Metrics footer */}
            <div className="grid grid-cols-3 gap-3 border-t border-slate-800/60 pt-4 mt-6">
              <div className="bg-slate-950/40 rounded-xl px-3.5 py-2.5 border border-slate-800/40 text-center flex flex-col">
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-center gap-1 mb-0.5">
                  <FileText className="h-3 w-3 text-violet-400" /> Chunks
                </span>
                <span className="text-sm font-display font-bold text-slate-200">{result.chunks_used} fragments</span>
              </div>
              <div className="bg-slate-950/40 rounded-xl px-3.5 py-2.5 border border-slate-800/40 text-center flex flex-col">
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-center gap-1 mb-0.5">
                  <Cpu className="h-3 w-3 text-indigo-400" /> Brain Model
                </span>
                <span className="text-sm font-display font-bold text-slate-200 truncate" title={result.provider}>
                  {result.provider.split("/").pop()}
                </span>
              </div>
              <div className="bg-slate-950/40 rounded-xl px-3.5 py-2.5 border border-slate-800/40 text-center flex flex-col">
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-center gap-1 mb-0.5">
                  <Compass className="h-3 w-3 text-fuchsia-400" /> Video Citations
                </span>
                <span className="text-sm font-display font-bold text-slate-200">{result.sources.length} sources</span>
              </div>
            </div>
          </div>

          {/* Sources Section */}
          {result.sources && result.sources.length > 0 && (
            <div className="flex flex-col gap-3">
              <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <Layers className="h-3.5 w-3.5" /> Cited Source Material
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {result.sources.map((src, i) => {
                  const ytUrl = `https://youtube.com/watch?v=${src.video_youtube_id}&t=${src.start_second}s`;
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
                        <span className="text-[9px] font-mono font-bold text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/15 shrink-0 shadow-sm" title="Reciprocal Rank Fusion Score">
                          RRF {src.rrf_score.toFixed(4)}
                        </span>
                      </div>

                      <div className="flex items-center justify-between mt-auto pt-3 border-t border-slate-850/60">
                        <span className="text-xs text-slate-500 font-semibold truncate max-w-[170px]">
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
          )}
        </div>
      )}
    </div>
  );
};
