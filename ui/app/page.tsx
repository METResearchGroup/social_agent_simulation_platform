'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import SignIn from '@/components/auth/SignIn';
import SimulationLayout from '@/components/layout/SimulationLayout';
import { RunDetailProvider } from '@/components/run-detail/RunDetailContext';
import RunDetailView from '@/components/run-detail/RunDetailView';
import AgentsView from '@/components/agents/AgentsView';
import RunHistorySidebar from '@/components/sidebars/RunHistorySidebar';
import StartView from '@/components/start/StartView';
import { useAuth } from '@/contexts/AuthContext';
import { useSimulationPageState } from '@/hooks/useSimulationPageState';
import { getDefaultConfig } from '@/lib/api/simulation';
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
    agentsError,
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
    handleRetryTurns,
  } = useSimulationPageState();

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
      onSelectTurn: handleSelectTurn,
      onRetryTurns:
        selectedRunId !== null
          ? () => handleRetryTurns(selectedRunId)
          : () => {
              /* no-op when no run selected */
            },
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
      handleSelectTurn,
      handleRetryTurns,
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
        agentsError={agentsError}
        onRetryAgents={handleRetryAgents}
        selectedAgentHandle={selectedAgentHandle}
        onSelectAgent={handleSelectAgent}
      />

      {viewMode === 'agents' ? (
        <AgentsView
          agents={agents}
          selectedAgentHandle={selectedAgentHandle}
          agentsLoading={agentsLoading}
          agentsError={agentsError}
          onRetryAgents={handleRetryAgents}
        />
      ) : isStartScreen ? (
        defaultConfigLoading && defaultConfig === null ? (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-beige-600">
            <LoadingSpinner />
            <span className="text-sm">Loading form…</span>
          </div>
        ) : defaultConfigError ? (
          <div className="flex flex-col gap-3 p-8 text-beige-800">
            <p className="text-sm">{defaultConfigError.message}</p>
            <button
              type="button"
              onClick={fetchDefaultConfig}
              className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
            >
              Retry
            </button>
            <StartView
              onSubmit={handleConfigSubmit}
              defaultConfig={defaultConfig ?? FALLBACK_DEFAULT_CONFIG}
            />
          </div>
        ) : (
          <StartView
            onSubmit={handleConfigSubmit}
            defaultConfig={defaultConfig ?? FALLBACK_DEFAULT_CONFIG}
          />
        )
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
