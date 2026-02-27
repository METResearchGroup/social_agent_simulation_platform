'use client';

import AgentDetail from '@/components/details/AgentDetail';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { Agent } from '@/types';

interface AgentsViewProps {
  agents: Agent[];
  selectedAgentHandle: string | null;
  agentsLoading: boolean;
  agentsError: Error | null;
  onRetryAgents: () => void;
}

export default function AgentsView({
  agents,
  selectedAgentHandle,
  agentsLoading,
  agentsError,
  onRetryAgents,
}: AgentsViewProps) {
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

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        <h3 className="text-lg font-medium text-beige-900 mb-4">Agent {agent.name}</h3>
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
