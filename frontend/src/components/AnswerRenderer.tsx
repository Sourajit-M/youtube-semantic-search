import React from "react";
import { FileText, Cpu, Compass, MessageSquare } from "lucide-react";
import type { AskResponse } from "../types";

interface AnswerRendererProps {
  result: AskResponse;
}

export const AnswerRenderer: React.FC<AnswerRendererProps> = ({ result }) => {
  const parseInline = (chunk: string): React.ReactNode[] => {
    const regex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
    const parts = chunk.split(regex);
    
    return parts.map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={index} className="font-semibold text-white">
            {part.slice(2, -2)}
          </strong>
        );
      } else if (part.startsWith("*") && part.endsWith("*")) {
        return <em key={index} className="italic text-slate-300">{part.slice(1, -1)}</em>;
      } else if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code key={index} className="bg-slate-950/60 border border-slate-800/80 rounded-md px-1.5 py-0.5 text-xs font-mono text-indigo-300 animate-pulse-slow">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  const formatAnswer = (text: string) => {
    const blocks = text.split("\n\n");

    return blocks.map((block, i) => {
      const lines = block.split("\n");
      const isList = lines.every(line => line.trim().startsWith("-") || line.trim().startsWith("*"));

      if (isList) {
        return (
          <ul key={i} className="list-disc pl-5 mb-4 space-y-1.5 text-slate-200 text-sm md:text-base font-normal">
            {lines.map((line, lineIdx) => {
              const cleaned = line.replace(/^\s*[-*]\s+/, "");
              return (
                <li key={lineIdx} className="leading-relaxed">
                  {parseInline(cleaned)}
                </li>
              );
            })}
          </ul>
        );
      }

      return (
        <p key={i} className="mb-4 text-slate-200 leading-relaxed text-sm md:text-base font-normal last:mb-0">
          {lines.map((line, lineIdx) => (
            <React.Fragment key={lineIdx}>
              {lineIdx > 0 && <br />}
              {parseInline(line)}
            </React.Fragment>
          ))}
        </p>
      );
    });
  };

  return (
    <div className="glass-panel border-slate-800/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 left-0 w-1.5 h-full bg-linear-to-b from-violet-600 to-indigo-500" />
      
      {/* Header info */}
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="h-4.5 w-4.5 text-violet-400" />
        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Grounded Synthesis</span>
      </div>

      {/* Answer text */}
      <div className="text-slate-100 leading-relaxed font-sans text-left">
        {formatAnswer(result.answer)}
      </div>

      {/* Metrics footer */}
      <div className="grid grid-cols-3 gap-3 border-t border-slate-800/60 pt-4 mt-6">
        <div className="bg-slate-950/40 rounded-xl px-3.5 py-2.5 border border-slate-800/40 text-center flex flex-col justify-center">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-center gap-1 mb-0.5">
            <FileText className="h-3 w-3 text-violet-400" /> Chunks
          </span>
          <span className="text-sm font-display font-bold text-slate-200">{result.chunks_used} fragments</span>
        </div>
        <div className="bg-slate-950/40 rounded-xl px-3.5 py-2.5 border border-slate-800/40 text-center flex flex-col justify-center">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-center gap-1 mb-0.5">
            <Cpu className="h-3 w-3 text-indigo-400" /> Brain Model
          </span>
          <span className="text-sm font-display font-bold text-slate-200 truncate" title={result.provider}>
            {result.provider.split("/").pop()}
          </span>
        </div>
        <div className="bg-slate-950/40 rounded-xl px-3.5 py-2.5 border border-slate-800/40 text-center flex flex-col justify-center">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center justify-center gap-1 mb-0.5">
            <Compass className="h-3 w-3 text-fuchsia-400" /> Video Citations
          </span>
          <span className="text-sm font-display font-bold text-slate-200">{result.sources.length} sources</span>
        </div>
      </div>
    </div>
  );
};
