'use client';

import AgentDetail from '@/components/details/AgentDetail';
import RunParametersBlock from '@/components/details/RunParametersBlock';
import RunSummary from '@/components/details/RunSummary';
import { useRunDetail } from '@/components/run-detail/RunDetailContext';
import { getPostByUri } from '@/lib/dummy-data';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { Agent, Post, Turn } from '@/types';

export default function DetailsPanel() {
  const {
    selectedRun,
    currentTurn,
    selectedTurn,
    currentRunConfig,
    runAgents,
    completedTurnsCount,
    turnsLoading,
    turnsError,
    onRetryTurns,
  } = useRunDetail();

  if (!selectedRun) {
    return (
      <div className="flex-1 flex items-center justify-center text-beige-600">
        Select a run to view details
      </div>
    );
  }

  if (turnsLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 text-beige-600">
        <LoadingSpinner />
        <span className="text-sm">Loading turns…</span>
      </div>
    );
  }

  if (turnsError) {
    const turnsErrorMessage = "Cannot load turns data. Please try again.";
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-beige-800">
        <p className="text-sm">{turnsErrorMessage}</p>
        <button
          type="button"
          onClick={onRetryTurns}
          className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
        >
          Retry
        </button>
      </div>
    );
  }

  if (selectedTurn === 'summary' || selectedTurn === null) {
    return (
      <RunSummary
        run={selectedRun}
        agents={runAgents}
        completedTurns={completedTurnsCount}
      />
    );
  }

  if (!currentTurn) {
    return (
      <div className="flex-1 flex items-center justify-center text-beige-600">
        No turn data available
      </div>
    );
  }

  const allPosts: Post[] = getAllPostsForTurn(currentTurn);
  const participatingAgents: Agent[] = getParticipatingAgents(currentTurn, runAgents);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <RunParametersBlock config={currentRunConfig} />
      <div className="flex-1 overflow-y-auto p-6">
        <h3 className="text-lg font-medium text-beige-900 mb-4">Agents</h3>
        <div className="space-y-4">
          {participatingAgents.map((agent) => {
            const feed = currentTurn.agentFeeds[agent.handle];
            const feedPosts: Post[] = feed
              ? feed.postUris
                  .map((uri) => getPostByUri(uri))
                  .filter((post): post is Post => post !== undefined)
              : [];
            const agentActions = currentTurn.agentActions[agent.handle] || [];

            return (
              <div key={agent.handle} className="border border-beige-300 rounded-lg p-3">
                <div className="font-medium text-beige-900 mb-2">
                  Agent {agent.name}
                </div>
                <AgentDetail
                  agent={agent}
                  feed={feedPosts}
                  actions={agentActions}
                  allPosts={allPosts}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function getAllPostsForTurn(turn: Turn): Post[] {
  return Object.values(turn.agentFeeds)
    .flatMap((feed) => feed.postUris.map((uri) => getPostByUri(uri)))
    .filter((post): post is Post => post !== undefined);
}

function getParticipatingAgents(turn: Turn, runAgents: Agent[]): Agent[] {
  const participatingAgentHandles: Set<string> = new Set([
    ...Object.keys(turn.agentFeeds),
    ...Object.keys(turn.agentActions),
  ]);
  return runAgents.filter((agent) => participatingAgentHandles.has(agent.handle));
}
