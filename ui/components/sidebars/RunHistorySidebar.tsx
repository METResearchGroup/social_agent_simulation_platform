'use client';

import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import type { ViewMode } from '@/hooks/useSimulationPageState';
import { Agent, Run } from '@/types';

interface RunHistorySidebarProps {
  runs: Run[];
  runsLoading: boolean;
  runsError: Error | null;
  onRetryRuns: () => void;
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  onStartNewRun: () => void;
  viewMode: ViewMode;
  onSetViewMode: (mode: ViewMode) => void;
  agents: Agent[];
  agentsLoading: boolean;
  agentsLoadingMore: boolean;
  agentsHasMore: boolean;
  agentsError: Error | null;
  onRetryAgents: () => void;
  onLoadMoreAgents: () => void;
  selectedAgentHandle: string | null;
  onSelectAgent: (handle: string | null) => void;
}

export default function RunHistorySidebar({
  runs,
  runsLoading,
  runsError,
  onRetryRuns,
  selectedRunId,
  onSelectRun,
  onStartNewRun,
  viewMode,
  onSetViewMode,
  agents,
  agentsLoading,
  agentsLoadingMore,
  agentsHasMore,
  agentsError,
  onRetryAgents,
  onLoadMoreAgents,
  selectedAgentHandle,
  onSelectAgent,
}: RunHistorySidebarProps) {
  const { user, signOut } = useAuth();

  const agentListContent = (): React.ReactNode => {
    if (agentsLoading && agents.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-8 text-beige-600">
          <LoadingSpinner />
          <span className="text-sm">Loading agents…</span>
        </div>
      );
    }
    if (agentsError) {
      return (
        <div className="flex flex-col gap-3 p-4 text-beige-800">
          <p className="text-sm">{agentsError.message}</p>
          <button
            type="button"
            onClick={onRetryAgents}
            className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
          >
            Retry
          </button>
        </div>
      );
    }
    if (agents.length === 0) {
      return (
        <p className="py-8 text-center text-sm text-beige-600">No agents</p>
      );
    }
    return (
      <>
        {agents.map((agent) => (
          <button
            key={agent.handle}
            type="button"
            data-testid={`agent-${agent.handle}`}
            onClick={() => onSelectAgent(agent.handle)}
            className={`w-full text-left p-3 border-b border-beige-200 hover:bg-beige-100 transition-colors ${
              selectedAgentHandle === agent.handle ? 'bg-beige-200' : ''
            }`}
          >
            <div className="text-sm font-medium text-beige-900 truncate">
              {agent.name}
            </div>
            <div className="text-xs text-beige-600 mt-1">{agent.handle}</div>
          </button>
        ))}
        {agentsHasMore ? (
          <div className="p-3">
            <button
              type="button"
              onClick={onLoadMoreAgents}
              disabled={agentsLoadingMore}
              className="w-full px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {agentsLoadingMore ? 'Loading…' : 'Load more'}
            </button>
          </div>
        ) : null}
      </>
    );
  };

  const runListContent = (): React.ReactNode => {
    if (runsLoading && runs.length === 0) {
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
        data-testid={`run-${run.runId}`}
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
        <div className="flex gap-1 mb-3">
          <button
            type="button"
            onClick={() => onSetViewMode('runs')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded transition-colors ${
              viewMode === 'runs'
                ? 'bg-beige-200 text-beige-900'
                : 'text-beige-600 hover:bg-beige-100'
            }`}
          >
            View runs
          </button>
          <button
            type="button"
            onClick={() => onSetViewMode('agents')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded transition-colors ${
              viewMode === 'agents'
                ? 'bg-beige-200 text-beige-900'
                : 'text-beige-600 hover:bg-beige-100'
            }`}
          >
            View agents
          </button>
          <button
            type="button"
            onClick={() => onSetViewMode('create-agent')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded transition-colors ${
              viewMode === 'create-agent'
                ? 'bg-beige-200 text-beige-900'
                : 'text-beige-600 hover:bg-beige-100'
            }`}
          >
            Create agent
          </button>
        </div>
        <h2 className="text-sm font-medium text-beige-900 mb-3">
          {viewMode === 'runs'
            ? 'Run History'
            : viewMode === 'create-agent'
              ? 'Create New Agent'
              : 'Agents'}
        </h2>
        {viewMode === 'runs' && (
          <button
            type="button"
            onClick={onStartNewRun}
            className="w-full px-3 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-hover transition-colors"
          >
            Start New Run
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto">
        {viewMode === 'runs' ? runListContent() : agentListContent()}
      </div>
      {user != null && (
        <div className="p-3 border-t border-beige-300">
          <p className="truncate text-xs text-beige-600 mb-2" title={user.email ?? undefined}>
            {user.email ?? user.id}
          </p>
          <button
            type="button"
            onClick={() => void signOut()}
            className="w-full px-3 py-2 text-sm font-medium text-beige-700 hover:text-beige-900 hover:bg-beige-200 rounded transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
