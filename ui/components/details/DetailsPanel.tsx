'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AgentDetail from '@/components/details/AgentDetail';
import RunParametersBlock from '@/components/details/RunParametersBlock';
import RunSummary from '@/components/details/RunSummary';
import { useRunDetail } from '@/components/run-detail/RunDetailContext';
import { getPosts } from '@/lib/api/simulation';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getTurnsErrorMessage } from '@/lib/error-messages';
import { Agent, ApiError, Post, RunConfig, Turn } from '@/types';

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
    runDetailsLoading,
    runDetailsError,
    onRetryTurns,
    onRetryRunDetails,
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
    const turnsErrorMessage = getTurnsErrorMessage(turnsError);
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

  return (
    <TurnDetailContent
      currentTurn={currentTurn}
      currentRunConfig={currentRunConfig}
      runAgents={runAgents}
      runDetailsLoading={runDetailsLoading}
      runDetailsError={runDetailsError}
      onRetryRunDetails={onRetryRunDetails}
    />
  );
}

function normalizeHandle(handle: string): string {
  return handle.startsWith('@') ? handle.slice(1) : handle;
}

function getPostIdsFromTurn(turn: Turn): string[] {
  const postIds: string[] = [];
  const seen = new Set<string>();
  for (const feed of Object.values(turn.agentFeeds)) {
    for (const postId of feed.postIds) {
      if (!seen.has(postId)) {
        seen.add(postId);
        postIds.push(postId);
      }
    }
  }
  for (const actions of Object.values(turn.agentActions)) {
    for (const action of actions) {
      if (!action.postId) continue;
      if (!seen.has(action.postId)) {
        seen.add(action.postId);
        postIds.push(action.postId);
      }
    }
  }
  return postIds;
}

interface TurnDetailContentProps {
  currentTurn: Turn;
  currentRunConfig: RunConfig | null;
  runAgents: Agent[];
  runDetailsLoading: boolean;
  runDetailsError: ApiError | null;
  onRetryRunDetails: () => void;
}

function TurnDetailContent({
  currentTurn,
  currentRunConfig,
  runAgents,
  runDetailsLoading,
  runDetailsError,
  onRetryRunDetails,
}: TurnDetailContentProps) {
  const postIds: string[] = useMemo(
    () => getPostIdsFromTurn(currentTurn),
    [currentTurn],
  );
  const [postsById, setPostsById] = useState<Record<string, Post>>({});
  const [postsLoading, setPostsLoading] = useState(true);
  const [postsError, setPostsError] = useState<Error | null>(null);
  const requestIdRef = useRef(0);

  const loadPosts = useCallback(async () => {
    if (postIds.length === 0) {
      setPostsById({});
      setPostsLoading(false);
      setPostsError(null);
      return;
    }
    requestIdRef.current += 1;
    const requestId = requestIdRef.current;
    setPostsLoading(true);
    setPostsError(null);
    try {
      const posts: Post[] = await getPosts(postIds);
      if (requestId !== requestIdRef.current) return;
      const byId: Record<string, Post> = {};
      for (const post of posts) {
        byId[post.postId] = post;
      }
      setPostsById(byId);
    } catch (error: unknown) {
      if (requestId !== requestIdRef.current) return;
      setPostsError(
        error instanceof Error ? error : new Error(String(error)),
      );
    } finally {
      if (requestId === requestIdRef.current) {
        setPostsLoading(false);
      }
    }
  }, [postIds]);

  useEffect(() => {
    void loadPosts();
  }, [loadPosts]);

  if (postsLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 text-beige-600">
        <LoadingSpinner />
        <span className="text-sm">Loading posts…</span>
      </div>
    );
  }

  if (postsError) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-beige-800">
        <p className="text-sm">Cannot load posts. Please try again.</p>
        <button
          type="button"
          onClick={() => void loadPosts()}
          className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
        >
          Retry
        </button>
      </div>
    );
  }

  const participatingAgents: Agent[] = getParticipatingAgents(
    currentTurn,
    runAgents,
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <RunParametersBlock
        config={currentRunConfig}
        runDetailsLoading={runDetailsLoading}
        runDetailsError={runDetailsError}
        onRetryRunDetails={onRetryRunDetails}
      />
      <div className="flex-1 overflow-y-auto p-6">
        <h3 className="text-lg font-medium text-beige-900 mb-4">Agents</h3>
        <div className="space-y-4">
          {participatingAgents.map((agent) => {
            const handleKey = normalizeHandle(agent.handle);
            const feed = currentTurn.agentFeeds[handleKey] || currentTurn.agentFeeds[agent.handle];
            const feedPosts: Post[] = feed
              ? feed.postIds
                  .map((postId) => postsById[postId])
                  .filter((post): post is Post => post !== undefined)
              : [];
            const agentActions =
              currentTurn.agentActions[handleKey] ||
              currentTurn.agentActions[agent.handle] ||
              [];

            return (
              <div key={agent.handle} className="border border-beige-300 rounded-lg p-3">
                <div className="font-medium text-beige-900 mb-2">
                  Agent {agent.name}
                </div>
                <AgentDetail
                  agent={agent}
                  feed={feedPosts}
                  actions={agentActions}
                  postsById={postsById}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function getParticipatingAgents(turn: Turn, runAgents: Agent[]): Agent[] {
  const participatingAgentHandles: Set<string> = new Set(
    [...Object.keys(turn.agentFeeds), ...Object.keys(turn.agentActions)].map(
      normalizeHandle,
    ),
  );
  return runAgents.filter((agent) =>
    participatingAgentHandles.has(normalizeHandle(agent.handle)),
  );
}
