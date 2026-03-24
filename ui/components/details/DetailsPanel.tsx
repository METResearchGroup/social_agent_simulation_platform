'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AgentDetail from '@/components/details/AgentDetail';
import RunParametersBlock from '@/components/details/RunParametersBlock';
import RunSummary from '@/components/details/RunSummary';
import { useRunDetail } from '@/components/run-detail/RunDetailContext';
import { getPosts } from '@/lib/api/simulation';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getTurnsErrorMessage } from '@/lib/error-messages';
import { Agent, AgentAction, ApiError, Feed, Post, RunConfig, Turn } from '@/types';

/** Client-side pagination for turn participating agents (no API change). */
const TURN_DETAIL_AGENTS_PAGE_SIZE = 5;

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
  const feedsByHandle: Record<string, Feed> = useMemo(
    () => buildFeedsByHandle(currentTurn),
    [currentTurn],
  );
  const actionsByHandle: Record<string, AgentAction[]> = useMemo(
    () => buildActionsByHandle(currentTurn),
    [currentTurn],
  );
  const participatingAgents: Agent[] = useMemo(
    () => getParticipatingAgents(currentTurn, runAgents),
    [currentTurn, runAgents],
  );
  const postIds: string[] = useMemo(
    () => getPostIdsFromTurn(currentTurn),
    [currentTurn],
  );
  const [postsById, setPostsById] = useState<Record<string, Post>>({});
  const [postsLoading, setPostsLoading] = useState(true);
  const [postsError, setPostsError] = useState<Error | null>(null);
  const requestIdRef = useRef(0);
  const [agentsPageIndex, setAgentsPageIndex] = useState(0);
  const [expandedAgentByHandle, setExpandedAgentByHandle] = useState<
    Record<string, boolean>
  >({});

  const totalAgentPages = Math.max(
    1,
    Math.ceil(participatingAgents.length / TURN_DETAIL_AGENTS_PAGE_SIZE),
  );
  const clampedAgentPage = Math.min(agentsPageIndex, totalAgentPages - 1);

  useEffect(() => {
    setAgentsPageIndex(0);
    setExpandedAgentByHandle({});
  }, [currentTurn.turnNumber]);

  useEffect(() => {
    if (agentsPageIndex !== clampedAgentPage) {
      setAgentsPageIndex(clampedAgentPage);
    }
  }, [agentsPageIndex, clampedAgentPage]);

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

  const pageStart = clampedAgentPage * TURN_DETAIL_AGENTS_PAGE_SIZE;
  const pageEnd = Math.min(
    pageStart + TURN_DETAIL_AGENTS_PAGE_SIZE,
    participatingAgents.length,
  );
  const pagedAgents = participatingAgents.slice(
    pageStart,
    pageStart + TURN_DETAIL_AGENTS_PAGE_SIZE,
  );
  const showAgentPagination =
    participatingAgents.length > TURN_DETAIL_AGENTS_PAGE_SIZE;

  const toggleAgentExpanded = (handle: string) => {
    setExpandedAgentByHandle((prev) => ({
      ...prev,
      [handle]: !prev[handle],
    }));
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <RunParametersBlock
        config={currentRunConfig}
        runDetailsLoading={runDetailsLoading}
        runDetailsError={runDetailsError}
        onRetryRunDetails={onRetryRunDetails}
      />
      <div className="flex-1 min-h-0 overflow-y-auto p-6 flex flex-col">
        <h3 className="text-lg font-medium text-beige-900 mb-4">Agents</h3>
        <div className="space-y-4 flex-1 min-h-0">
          {pagedAgents.map((agent) => {
            const handleKey = normalizeHandle(agent.handle);
            const feed = feedsByHandle[handleKey];
            const feedPosts: Post[] = feed
              ? feed.postIds
                  .map((postId) => postsById[postId])
                  .filter((post): post is Post => post !== undefined)
              : [];
            const agentActions = actionsByHandle[handleKey] ?? [];
            const isExpanded = expandedAgentByHandle[agent.handle] === true;

            return (
              <div
                key={agent.handle}
                className="border border-beige-300 rounded-lg overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => toggleAgentExpanded(agent.handle)}
                  className="w-full text-left flex items-center justify-between gap-2 p-3 hover:bg-beige-100 transition-colors"
                >
                  <div className="flex flex-col items-start min-w-0 flex-1">
                    <span className="text-sm font-medium text-beige-900">
                      {agent.name}
                    </span>
                    <span className="text-xs text-beige-600">
                      @{normalizeHandle(agent.handle)}
                    </span>
                  </div>
                  <span className="text-beige-600 shrink-0" aria-hidden>
                    {isExpanded ? '▼' : '▶'}
                  </span>
                </button>
                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-beige-200">
                    <AgentDetail
                      agent={agent}
                      feed={feedPosts}
                      actions={agentActions}
                      postsById={postsById}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {showAgentPagination && (
          <div className="mt-4 pt-4 border-t border-beige-200 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between shrink-0">
            <div className="text-sm text-beige-700">
              Page {clampedAgentPage + 1} of {totalAgentPages}
              <span className="text-beige-500">
                {' '}
                · Showing {pageStart + 1}–{pageEnd} of{' '}
                {participatingAgents.length}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={clampedAgentPage === 0}
                onClick={() =>
                  setAgentsPageIndex((p) => Math.max(0, p - 1))
                }
                className="px-3 py-1.5 text-sm font-medium rounded border border-beige-300 text-beige-800 hover:bg-beige-100 disabled:opacity-40 disabled:pointer-events-none"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={clampedAgentPage >= totalAgentPages - 1}
                onClick={() =>
                  setAgentsPageIndex((p) =>
                    Math.min(totalAgentPages - 1, p + 1),
                  )
                }
                className="px-3 py-1.5 text-sm font-medium rounded border border-beige-300 text-beige-800 hover:bg-beige-100 disabled:opacity-40 disabled:pointer-events-none"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function collectHandlesFromTurn(turn: Turn): Set<string> {
  const handles = new Set<string>();
  for (const feed of Object.values(turn.agentFeeds)) {
    handles.add(normalizeHandle(feed.agentHandle));
  }
  for (const actions of Object.values(turn.agentActions)) {
    for (const action of actions) {
      handles.add(normalizeHandle(action.agentHandle));
    }
  }
  return handles;
}

function buildFeedsByHandle(turn: Turn): Record<string, Feed> {
  const byHandle: Record<string, Feed> = {};
  for (const feed of Object.values(turn.agentFeeds)) {
    byHandle[normalizeHandle(feed.agentHandle)] = feed;
  }
  return byHandle;
}

function buildActionsByHandle(turn: Turn): Record<string, AgentAction[]> {
  const byHandle: Record<string, AgentAction[]> = {};
  for (const actions of Object.values(turn.agentActions)) {
    for (const action of actions) {
      const h = normalizeHandle(action.agentHandle);
      if (byHandle[h] === undefined) {
        byHandle[h] = [];
      }
      byHandle[h].push(action);
    }
  }
  return byHandle;
}

function getParticipatingAgents(turn: Turn, runAgents: Agent[]): Agent[] {
  const participatingHandles = collectHandlesFromTurn(turn);
  return runAgents.filter((agent) =>
    participatingHandles.has(normalizeHandle(agent.handle)),
  );
}
