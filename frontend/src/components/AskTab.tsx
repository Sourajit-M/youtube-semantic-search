import React, { useState, useEffect, useRef } from "react";
import { Send, Sparkles, MessageSquare, AlertCircle } from "lucide-react";
import type { AskResponse } from "../types";
import { AnswerRenderer } from "./AnswerRenderer";
import { CitationsPanel } from "./CitationsPanel";
import { SourcesPanel } from "./SourcesPanel";
import { AskSkeleton } from "./AskSkeleton";

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

  const answerRef = useRef<HTMLDivElement>(null);

  // Phase 4: Auto-scroll to response when it loads
  useEffect(() => {
    if (result) {
      answerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload: Record<string, string | number> = {
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
    } catch (err) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : "An unexpected error occurred connecting to the RAG endpoint.";
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  // Phase 2: Compute Maximum RRF score for relevance normalization
  const maxRrf = result && result.sources && result.sources.length > 0
    ? Math.max(...result.sources.map((s) => s.rrf_score), 0.0001)
    : 1;

  return (
    <div className="flex-1 h-full overflow-y-auto flex flex-col p-6 md:p-8 space-y-6 max-w-5xl mx-auto w-full">
      {/* Title block */}
      <div className="flex flex-col gap-2">
        <h2 className="font-display font-extrabold text-2xl md:text-3xl bg-clip-text text-transparent bg-linear-to-r from-slate-50 via-slate-100 to-indigo-200">
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
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold shadow-lg shadow-violet-600/15 border border-violet-500/20 bg-linear-to-r from-violet-600 to-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:from-violet-500 hover:to-indigo-400 active:scale-97 cursor-pointer transition-all duration-300"
          >
            {loading ? (
              <>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-white typing-dot animate-bounce" />
                  <span className="h-1.5 w-1.5 rounded-full bg-white typing-dot animate-bounce [animation-delay:0.2s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-white typing-dot animate-bounce [animation-delay:0.4s]" />
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
        <div className="flex items-start gap-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 p-4.5 rounded-2xl animate-fade-in text-left">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
          <div className="text-sm leading-relaxed w-full">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold">Pipeline Query Error</span>
              <button 
                onClick={() => handleAsk(question)}
                className="text-xs text-rose-400 hover:text-rose-300 underline font-semibold transition-all"
              >
                Retry Request
              </button>
            </div>
            {error}
          </div>
        </div>
      )}

      {/* Phase 4: Empty State */}
      {!result && !loading && !error && (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-slate-900/10 border border-slate-800/40 rounded-2xl border-dashed py-12 animate-fade-in">
          <div className="bg-violet-600/15 p-4 rounded-full border border-violet-500/20 mb-4 animate-pulse">
            <MessageSquare className="h-8 w-8 text-violet-400" />
          </div>
          <h3 className="font-display font-bold text-lg text-slate-200 mb-1">Start a Conversation</h3>
          <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
            Ask any question about the indexed YouTube channels. The system will search transcripts and synthesize grounded answers with citations.
          </p>
        </div>
      )}

      {/* Phase 4: Synthesizing / Skeleton Loader UI */}
      {loading && <AskSkeleton />}

      {/* Answer Console Block */}
      {result && (
        <div ref={answerRef} className="flex flex-col gap-6 animate-fade-in">
          {/* Main Answer card */}
          <AnswerRenderer result={result} />

          {/* Phase 1: Citations stripped warning banner */}
          {result.sources && result.sources.length > 0 && (!result.citations || result.citations.length === 0) && (
            <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 text-amber-300 p-4.5 rounded-2xl animate-fade-in text-left">
              <AlertCircle className="h-5 w-5 shrink-0 text-amber-400 mt-0.5" />
              <div className="text-sm leading-relaxed">
                <span className="font-bold block mb-0.5">Citation Grounding</span>
                AI quotes were unavailable or stripped for accuracy. Underlying video sources are linked below.
              </div>
            </div>
          )}

          {/* Phase 1: Citations Quotes Panel */}
          {result.citations && result.citations.length > 0 && (
            <CitationsPanel citations={result.citations} sources={result.sources} />
          )}

          {/* Sources Section */}
          {result.sources && result.sources.length > 0 && (
            <SourcesPanel sources={result.sources} maxRrf={maxRrf} />
          )}
        </div>
      )}
    </div>
  );
};
