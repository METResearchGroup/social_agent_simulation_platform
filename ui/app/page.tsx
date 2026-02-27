'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import SignIn from '@/components/auth/SignIn';
import SimulationLayout from '@/components/layout/SimulationLayout';
import { RunDetailProvider } from '@/components/run-detail/RunDetailContext';
import RunDetailView from '@/components/run-detail/RunDetailView';
import AgentsView from '@/components/agents/AgentsView';
import CreateAgentView from '@/components/agents/CreateAgentView';
import RunHistorySidebar from '@/components/sidebars/RunHistorySidebar';
import StartScreenView from '@/components/start/StartScreenView';
import { useAuth } from '@/contexts/AuthContext';
import { useSimulationPageState } from '@/hooks/useSimulationPageState';
import { deleteAgent, getDefaultConfig, postAgent } from '@/lib/api/simulation';
import { FALLBACK_DEFAULT_CONFIG } from '@/lib/default-config';
import type { RunConfig } from '@/types';

function AuthenticatedApp() {
  const [defaultConfig, setDefaultConfig] = useState<RunConfig | null>(null);
  const [defaultConfigLoading, setDefaultConfigLoading] = useState<boolean>(true);
  const [defaultConfigError, setDefaultConfigError] = useState<Error | null>(null);

  const fetchDefaultConfig = useCallback(async (): Promise<void> => {
    setDefaultConfigLoading(true);
    setDefaultConfigError(null);
    try {
      const config = await getDefaultConfig();
      setDefaultConfig(config);
    } catch (err) {
      setDefaultConfigError(err instanceof Error ? err : new Error(String(err)));
      setDefaultConfig(FALLBACK_DEFAULT_CONFIG);
    } finally {
      setDefaultConfigLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDefaultConfig();
  }, [fetchDefaultConfig]);

  const {
    runsWithStatus,
    runsLoading,
    runsError,
    agents,
    agentsLoading,
    agentsLoadingMore,
    agentsError,
    agentsHasMore,
    agentsQuery,
    turnsLoadingByRunId,
    turnsErrorByRunId,
    viewMode,
    selectedAgentHandle,
    selectedRunId,
    selectedTurn,
    selectedRun,
    currentTurn,
    availableTurns,
    completedTurnsCount,
    runAgents,
    currentRunConfig,
    isStartScreen,
    handleConfigSubmit,
    handleSetViewMode,
    handleSelectAgent,
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
    handleRetryRuns,
    handleRetryAgents,
    handleLoadMoreAgents,
    handleSetAgentsQuery,
    handleRetryTurns,
    runDetailsLoading,
    runDetailsError,
    handleRetryRunDetails,
  } = useSimulationPageState();

  const handleCreateAgent = useCallback(
    async (payload: {
      handle: string;
      displayName: string;
      bio: string;
    }): Promise<void> => {
      const created = await postAgent({
        handle: payload.handle,
        display_name: payload.displayName,
        bio: payload.bio,
      });
      handleRetryAgents();
      handleSetViewMode('agents');
      handleSelectAgent(created.handle);
    },
    [handleRetryAgents, handleSetViewMode, handleSelectAgent],
  );

  const handleDeleteAgent = useCallback(
    async (handle: string): Promise<void> => {
      await deleteAgent(handle);
      handleSelectAgent(null);
      handleRetryAgents();
    },
    [handleRetryAgents, handleSelectAgent],
  );

  const runDetailContextValue = useMemo(
    () => ({
      selectedRun,
      currentTurn,
      selectedTurn,
      availableTurns,
      currentRunConfig,
      runAgents,
      completedTurnsCount,
      turnsLoading: selectedRunId ? (turnsLoadingByRunId[selectedRunId] ?? false) : false,
      turnsError: selectedRunId ? (turnsErrorByRunId[selectedRunId] ?? null) : null,
      runDetailsLoading,
      runDetailsError,
      onSelectTurn: handleSelectTurn,
      onRetryTurns:
        selectedRunId !== null
          ? () => handleRetryTurns(selectedRunId)
          : () => {
              /* no-op when no run selected */
            },
      onRetryRunDetails: handleRetryRunDetails,
    }),
    [
      selectedRun,
      currentTurn,
      selectedTurn,
      availableTurns,
      currentRunConfig,
      runAgents,
      completedTurnsCount,
      selectedRunId,
      turnsLoadingByRunId,
      turnsErrorByRunId,
      runDetailsLoading,
      runDetailsError,
      handleSelectTurn,
      handleRetryTurns,
      handleRetryRunDetails,
    ],
  );

  return (
    <SimulationLayout>
      <RunHistorySidebar
        runs={runsWithStatus}
        runsLoading={runsLoading}
        runsError={runsError}
        onRetryRuns={handleRetryRuns}
        selectedRunId={selectedRunId}
        onSelectRun={handleSelectRun}
        onStartNewRun={handleStartNewRun}
        viewMode={viewMode}
        onSetViewMode={handleSetViewMode}
        agents={agents}
        agentsLoading={agentsLoading}
        agentsLoadingMore={agentsLoadingMore}
        agentsHasMore={agentsHasMore}
        agentsError={agentsError}
        agentsQuery={agentsQuery}
        onRetryAgents={handleRetryAgents}
        onLoadMoreAgents={handleLoadMoreAgents}
        onAgentsQueryChange={handleSetAgentsQuery}
        selectedAgentHandle={selectedAgentHandle}
        onSelectAgent={handleSelectAgent}
      />

      {viewMode === 'create-agent' ? (
        <CreateAgentView onSubmit={handleCreateAgent} />
      ) : viewMode === 'agents' ? (
        <AgentsView
          agents={agents}
          selectedAgentHandle={selectedAgentHandle}
          agentsLoading={agentsLoading}
          agentsError={agentsError}
          onRetryAgents={handleRetryAgents}
          onDeleteAgent={handleDeleteAgent}
        />
      ) : isStartScreen ? (
        <StartScreenView
          defaultConfig={defaultConfig}
          defaultConfigLoading={defaultConfigLoading}
          defaultConfigError={defaultConfigError}
          onRetryConfig={fetchDefaultConfig}
          onSubmit={handleConfigSubmit}
        />
      ) : (
        <RunDetailProvider value={runDetailContextValue}>
          <RunDetailView />
        </RunDetailProvider>
      )}
    </SimulationLayout>
  );
}

export default function Home() {
  const { user, isLoading: authLoading } = useAuth();

  if (authLoading || !user) {
    return (
      <SimulationLayout>
        <SignIn />
      </SimulationLayout>
    );
  }

  return (
    <SimulationLayout>
      <AuthenticatedApp />
    </SimulationLayout>
  );
}
