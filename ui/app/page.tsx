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
    selectedRunId,
    selectedTurn,
    selectedRun,
    currentTurn,
    availableTurns,
    completedTurnsCount,
    runAgents,
    currentRunConfig,
    isStartScreen,
    turnsError,
    retryTurns,
    handleConfigSubmit,
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
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
      turnsError,
      retryTurns,
      onSelectTurn: handleSelectTurn,
    }),
    [
      selectedRun,
      currentTurn,
      selectedTurn,
      availableTurns,
      currentRunConfig,
      runAgents,
      completedTurnsCount,
      turnsError,
      retryTurns,
      handleSelectTurn,
    ],
  );

  return (
    <SimulationLayout>
      <RunHistorySidebar
        runs={runsWithStatus}
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
