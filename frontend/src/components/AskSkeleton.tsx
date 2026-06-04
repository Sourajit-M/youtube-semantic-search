import React from "react";

export const AskSkeleton: React.FC = () => {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      {/* Answer Card Skeleton */}
      <div className="glass-panel border-slate-800/80 rounded-2xl p-6 relative overflow-hidden bg-slate-900/20">
        <div className="absolute top-0 left-0 w-1.5 h-full bg-slate-850" />
        <div className="h-4 w-32 bg-slate-800 rounded mb-4" />
        <div className="space-y-2 mb-6">
          <div className="h-3.5 w-full bg-slate-800 rounded" />
          <div className="h-3.5 w-5/6 bg-slate-800 rounded" />
          <div className="h-3.5 w-4/5 bg-slate-800 rounded" />
          <div className="h-3.5 w-11/12 bg-slate-800 rounded" />
        </div>
        <div className="grid grid-cols-3 gap-3 border-t border-slate-800/60 pt-4">
          <div className="h-12 bg-slate-950/40 rounded-xl border border-slate-800/40" />
          <div className="h-12 bg-slate-950/40 rounded-xl border border-slate-800/40" />
          <div className="h-12 bg-slate-950/40 rounded-xl border border-slate-800/40" />
        </div>
      </div>
      
      {/* Sources Skeleton */}
      <div className="space-y-3">
        <div className="h-3.5 w-40 bg-slate-800 rounded" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div className="h-28 bg-slate-900/35 border border-slate-800/70 rounded-2xl" />
          <div className="h-28 bg-slate-900/35 border border-slate-800/70 rounded-2xl" />
        </div>
      </div>
    </div>
  );
};
