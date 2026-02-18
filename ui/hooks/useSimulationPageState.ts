'use client';

import { useMemo, useState } from 'react';
import {
  DUMMY_AGENTS,
  DUMMY_RUNS,
  DUMMY_TURNS,
} from '@/lib/dummy-data';
import {
  getAvailableTurns,
  getCompletedTurnsCount,
  getCurrentTurn,
  getRunAgents,
  getRunConfig,
  withComputedRunStatuses,
} from '@/lib/run-selectors';
import { Run, RunConfig, Turn } from '@/types';

const EMPTY_RUN_CONFIGS: Record<string, RunConfig> = {};
const EMPTY_NEW_RUN_TURNS: Record<string, Record<string, Turn>> = {};

interface UseSimulationPageStateResult {
  runsWithStatus: Run[];
  selectedRunId: string | null;
  selectedTurn: number | 'summary' | null;
  selectedRun: Run | null;
  currentTurn: Turn | null;
  availableTurns: number[];
  completedTurnsCount: number;
  runAgents: typeof DUMMY_AGENTS;
  currentRunConfig: RunConfig | null;
  isStartScreen: boolean;
  handleConfigSubmit: (config: RunConfig) => void;
  handleSelectRun: (runId: string) => void;
  handleSelectTurn: (turn: number | 'summary') => void;
  handleStartNewRun: () => void;
}

export function useSimulationPageState(): UseSimulationPageStateResult {
  const [runs, setRuns] = useState<Run[]>(() =>
    withComputedRunStatuses(DUMMY_RUNS),
  );
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedTurn, setSelectedTurn] = useState<number | 'summary' | null>(null);
  const [runConfigs, setRunConfigs] = useState<Record<string, RunConfig>>(EMPTY_RUN_CONFIGS);
  const [newRunTurns] = useState<Record<string, Record<string, Turn>>>(EMPTY_NEW_RUN_TURNS);

  const runsWithStatus: Run[] = useMemo(
    () => withComputedRunStatuses(runs),
    [runs],
  );

  const selectedRun: Run | null = useMemo(
    () => runsWithStatus.find((run) => run.runId === selectedRunId) || null,
    [runsWithStatus, selectedRunId],
  );

  const currentTurn: Turn | null = useMemo(
    () => getCurrentTurn(selectedRunId, selectedTurn, newRunTurns, DUMMY_TURNS),
    [selectedRunId, selectedTurn, newRunTurns],
  );

  const availableTurns: number[] = useMemo(
    () => getAvailableTurns(selectedRunId, newRunTurns, DUMMY_TURNS),
    [selectedRunId, newRunTurns],
  );

  const completedTurnsCount: number = useMemo(
    () => getCompletedTurnsCount(selectedRunId, newRunTurns, DUMMY_TURNS),
    [selectedRunId, newRunTurns],
  );

  const runAgents = useMemo(
    () => getRunAgents(selectedRun, DUMMY_AGENTS),
    [selectedRun],
  );

  const currentRunConfig: RunConfig | null = useMemo(
    () => getRunConfig(selectedRun, runConfigs),
    [selectedRun, runConfigs],
  );

  const handleConfigSubmit = (config: RunConfig): void => {
    const now: Date = new Date();
    const newRunId: string = `run_${now.toISOString()}`;
    const newRun: Run = {
      runId: newRunId,
      createdAt: now.toISOString(),
      totalTurns: config.numTurns,
      totalAgents: config.numAgents,
      status: 'running',
    };

    setRuns((previousRuns) => [newRun, ...previousRuns]);
    setRunConfigs((previousConfigs) => ({ ...previousConfigs, [newRunId]: config }));
    setSelectedRunId(newRunId);
    setSelectedTurn('summary');
  };

  const handleSelectRun = (runId: string): void => {
    setSelectedRunId(runId);
    setSelectedTurn('summary');
  };

  const handleSelectTurn = (turn: number | 'summary'): void => {
    setSelectedTurn(turn);
  };

  const handleStartNewRun = (): void => {
    setSelectedRunId(null);
    setSelectedTurn(null);
  };

  return {
    runsWithStatus,
    selectedRunId,
    selectedTurn,
    selectedRun,
    currentTurn,
    availableTurns,
    completedTurnsCount,
    runAgents,
    currentRunConfig,
    isStartScreen: selectedRunId === null,
    handleConfigSubmit,
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
  };
}
