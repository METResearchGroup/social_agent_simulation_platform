'use client';

import { useEffect, useRef, useState } from 'react';
import AgentDetail from '@/components/details/AgentDetail';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { Agent } from '@/types';

interface AgentsViewProps {
  agents: Agent[];
  selectedAgentHandle: string | null;
  agentsLoading: boolean;
  agentsError: Error | null;
  onRetryAgents: () => void;
  onDeleteAgent: (handle: string) => Promise<void>;
}

export default function AgentsView({
  agents,
  selectedAgentHandle,
  agentsLoading,
  agentsError,
  onRetryAgents,
  onDeleteAgent,
}: AgentsViewProps) {
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const deleteRequestIdRef = useRef(0);

  useEffect(() => {
    deleteRequestIdRef.current += 1;
    setDeleteError(null);
    setIsDeleting(false);
  }, [selectedAgentHandle]);
  if (agentsLoading && agents.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 py-16 text-beige-600">
        <LoadingSpinner />
        <span className="text-sm">Loading agents…</span>
      </div>
    );
  }

  if (agentsError) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-beige-800">
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

  if (!selectedAgentHandle) {
    return (
      <div className="flex-1 flex items-center justify-center text-beige-600">
        Select an agent to view details
      </div>
    );
  }

  const agent: Agent | undefined = agents.find((a) => a.handle === selectedAgentHandle);
  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center text-beige-600">
        Agent not found
      </div>
    );
  }

  const handleDeleteClick = async (): Promise<void> => {
    if (isDeleting) {
      return;
    }
    setDeleteError(null);
    const confirmed = window.confirm(`Delete agent ${agent.name}?`);
    if (!confirmed) {
      return;
    }
    const requestId = deleteRequestIdRef.current + 1;
    deleteRequestIdRef.current = requestId;
    setIsDeleting(true);
    try {
      await onDeleteAgent(agent.handle);
    } catch (err) {
      if (deleteRequestIdRef.current !== requestId) {
        return;
      }
      setDeleteError(err instanceof Error ? err.message : String(err));
    } finally {
      if (deleteRequestIdRef.current !== requestId) {
        return;
      }
      setIsDeleting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 className="text-lg font-medium text-beige-900">Agent {agent.name}</h3>
            {deleteError ? (
              <div className="text-sm text-red-600 mt-1">{deleteError}</div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="px-3 py-2 text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-60"
          >
            {isDeleting ? 'Deleting…' : 'Delete agent'}
          </button>
        </div>
        <div className="border border-beige-300 rounded-lg p-3">
          <AgentDetail
            agent={agent}
            feed={[]}
            actions={[]}
            postsById={{}}
          />
        </div>
      </div>
    </div>
  );
}
