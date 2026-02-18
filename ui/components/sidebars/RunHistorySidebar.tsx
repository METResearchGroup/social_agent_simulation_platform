'use client';

import { Run } from '@/types';

interface RunHistorySidebarProps {
  runs: Run[];
  runsLoading: boolean;
  runsError: Error | null;
  onRetryRuns: () => void;
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  onStartNewRun: () => void;
}

function LoadingSpinner() {
  return (
    <div
      className="h-5 w-5 animate-spin rounded-full border-2 border-beige-300 border-t-accent"
      aria-hidden
    />
  );
}

export default function RunHistorySidebar({
  runs,
  runsLoading,
  runsError,
  onRetryRuns,
  selectedRunId,
  onSelectRun,
  onStartNewRun,
}: RunHistorySidebarProps) {
  const runListContent = (): React.ReactNode => {
    if (runsLoading) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-8 text-beige-600">
          <LoadingSpinner />
          <span className="text-sm">Loading runs…</span>
        </div>
      );
    }
    if (runsError) {
      return (
        <div className="flex flex-col gap-3 p-4 text-beige-800">
          <p className="text-sm">{runsError.message}</p>
          <button
            type="button"
            onClick={onRetryRuns}
            className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
          >
            Retry
          </button>
        </div>
      );
    }
    if (runs.length === 0) {
      return (
        <p className="py-8 text-center text-sm text-beige-600">No runs yet</p>
      );
    }
    return runs.map((run) => (
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
    ));
  };

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
      <div className="flex-1 overflow-y-auto">{runListContent()}</div>
    </div>
  );
}
