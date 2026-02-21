'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AgentDetail from '@/components/details/AgentDetail';
import RunParametersBlock from '@/components/details/RunParametersBlock';
import RunSummary from '@/components/details/RunSummary';
import { useRunDetail } from '@/components/run-detail/RunDetailContext';
import { getPosts } from '@/lib/api/simulation';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { getTurnsErrorMessage } from '@/lib/error-messages';
import { Agent, Post, RunConfig, Turn } from '@/types';

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
    />
  );
}

function getPostUrisFromTurn(turn: Turn): string[] {
  const uris: string[] = [];
  const seen = new Set<string>();
  for (const feed of Object.values(turn.agentFeeds)) {
    for (const uri of feed.postUris) {
      if (!seen.has(uri)) {
        seen.add(uri);
        uris.push(uri);
      }
    }
  }
  return uris;
}

function getAllPostsForTurn(
  turn: Turn,
  postsByUri: Record<string, Post>,
): Post[] {
  return Object.values(turn.agentFeeds)
    .flatMap((feed) =>
      feed.postUris
        .map((uri) => postsByUri[uri])
        .filter((post): post is Post => post !== undefined),
    );
}

interface TurnDetailContentProps {
  currentTurn: Turn;
  currentRunConfig: RunConfig | null;
  runAgents: Agent[];
}

function TurnDetailContent({
  currentTurn,
  currentRunConfig,
  runAgents,
}: TurnDetailContentProps) {
  const postUris: string[] = useMemo(
    () => getPostUrisFromTurn(currentTurn),
    [currentTurn],
  );
  const [postsByUri, setPostsByUri] = useState<Record<string, Post>>({});
  const [postsLoading, setPostsLoading] = useState(true);
  const [postsError, setPostsError] = useState<Error | null>(null);
  const requestIdRef = useRef(0);

  const loadPosts = useCallback(async () => {
    if (postUris.length === 0) {
      setPostsByUri({});
      setPostsLoading(false);
      setPostsError(null);
      return;
    }
    requestIdRef.current += 1;
    const requestId = requestIdRef.current;
    setPostsLoading(true);
    setPostsError(null);
    try {
      const posts: Post[] = await getPosts(postUris);
      if (requestId !== requestIdRef.current) return;
      const byUri: Record<string, Post> = {};
      for (const post of posts) {
        byUri[post.uri] = post;
      }
      setPostsByUri(byUri);
    } catch (error: unknown) {
      if (requestId !== requestIdRef.current) return;
      setPostsError(
        error instanceof Error ? error : new Error(String(error)),
      );
    } finally {
      if (requestId !== requestIdRef.current) return;
      setPostsLoading(false);
    }
  }, [postUris]);

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

  const allPosts: Post[] = getAllPostsForTurn(currentTurn, postsByUri);
  const participatingAgents: Agent[] = getParticipatingAgents(
    currentTurn,
    runAgents,
  );

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
                  .map((uri) => postsByUri[uri])
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

function getParticipatingAgents(turn: Turn, runAgents: Agent[]): Agent[] {
  const participatingAgentHandles: Set<string> = new Set([
    ...Object.keys(turn.agentFeeds),
    ...Object.keys(turn.agentActions),
  ]);
  return runAgents.filter((agent) => participatingAgentHandles.has(agent.handle));
}
