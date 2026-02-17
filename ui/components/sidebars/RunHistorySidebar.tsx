'use client';

import { Run } from '@/types';

interface RunHistorySidebarProps {
  runs: Run[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  onStartNewRun: () => void;
}

export default function RunHistorySidebar({
  runs,
  selectedRunId,
  onSelectRun,
  onStartNewRun,
}: RunHistorySidebarProps) {
  return (
    <div className="w-1/4 border-r border-beige-300 bg-beige-50 flex flex-col">
      <div className="p-4 border-b border-beige-300">
        <h2 className="text-sm font-medium text-beige-900 mb-3">Run History</h2>
        <button
          type="button"
          onClick={onStartNewRun}
          className="w-full px-3 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-hover transition-colors"
        >
          Start New Run
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {runs.map((run) => (
          <button
            key={run.runId}
            type="button"
            onClick={() => onSelectRun(run.runId)}
            className={`w-full text-left p-3 border-b border-beige-200 hover:bg-beige-100 transition-colors ${
              selectedRunId === run.runId ? 'bg-beige-200' : ''
            }`}
          >
            <div className="text-sm font-medium text-beige-900 truncate">
              {run.runId}
            </div>
            <div className="text-xs text-beige-600 mt-1">
              {run.totalAgents} agents • {run.totalTurns} turns
            </div>
            <div className="text-xs text-beige-500 mt-1 capitalize">
              {run.status}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
