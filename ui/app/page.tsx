'use client';

import { useMemo } from 'react';
import SimulationLayout from '@/components/layout/SimulationLayout';
import { RunDetailProvider } from '@/components/run-detail/RunDetailContext';
import RunDetailView from '@/components/run-detail/RunDetailView';
import RunHistorySidebar from '@/components/sidebars/RunHistorySidebar';
import StartView from '@/components/start/StartView';
import { useSimulationPageState } from '@/hooks/useSimulationPageState';
import { DEFAULT_CONFIG } from '@/lib/dummy-data';

export default function Home() {
  const {
    runsWithStatus,
    runsLoading,
    runsError,
    turnsLoadingByRunId,
    turnsErrorByRunId,
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
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
    handleRetryRuns,
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
      />

      {isStartScreen ? (
        <StartView onSubmit={handleConfigSubmit} defaultConfig={DEFAULT_CONFIG} />
      ) : (
        <RunDetailProvider value={runDetailContextValue}>
          <RunDetailView />
        </RunDetailProvider>
      )}
    </SimulationLayout>
  );
}
