'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  DUMMY_AGENTS,
} from '@/lib/dummy-data';
import {
  getRuns,
  getTurnsForRun,
} from '@/lib/api/simulation';
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
const EMPTY_FALLBACK_TURNS: Record<string, Record<string, Turn>> = {};

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
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedTurn, setSelectedTurn] = useState<number | 'summary' | null>(null);
  const [runConfigs, setRunConfigs] = useState<Record<string, RunConfig>>(EMPTY_RUN_CONFIGS);
  const [newRunTurns] = useState<Record<string, Record<string, Turn>>>(EMPTY_NEW_RUN_TURNS);
  const [fallbackTurns, setFallbackTurns] = useState<Record<string, Record<string, Turn>>>(
    EMPTY_FALLBACK_TURNS,
  );

  useEffect(() => {
    let isMounted: boolean = true;

    const loadRuns = async (): Promise<void> => {
      try {
        const apiRuns: Run[] = await getRuns();
        if (isMounted) {
          setRuns(apiRuns);
        }
      } catch (error) {
        console.error('Failed to fetch runs:', error);
      }
    };

    void loadRuns();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId || fallbackTurns[selectedRunId]) {
      return;
    }

    let isMounted: boolean = true;

    const loadTurnsForRun = async (): Promise<void> => {
      try {
        const turnsForRun: Record<string, Turn> = await getTurnsForRun(selectedRunId);
        if (isMounted) {
          setFallbackTurns((previousTurns) => ({
            ...previousTurns,
            [selectedRunId]: turnsForRun,
          }));
        }
      } catch (error) {
        console.error(`Failed to fetch turns for ${selectedRunId}:`, error);
        if (isMounted) {
          setFallbackTurns((previousTurns) => ({
            ...previousTurns,
            [selectedRunId]: {},
          }));
        }
      }
    };

    void loadTurnsForRun();

    return () => {
      isMounted = false;
    };
  }, [selectedRunId, fallbackTurns]);

  const runsWithStatus: Run[] = useMemo(
    () => withComputedRunStatuses(runs),
    [runs],
  );

  const selectedRun: Run | null = useMemo(
    () => runsWithStatus.find((run) => run.runId === selectedRunId) || null,
    [runsWithStatus, selectedRunId],
  );

  const currentTurn: Turn | null = useMemo(
    () => getCurrentTurn(selectedRunId, selectedTurn, newRunTurns, fallbackTurns),
    [selectedRunId, selectedTurn, newRunTurns, fallbackTurns],
  );

  const availableTurns: number[] = useMemo(
    () => getAvailableTurns(selectedRunId, newRunTurns, fallbackTurns),
    [selectedRunId, newRunTurns, fallbackTurns],
  );

  const completedTurnsCount: number = useMemo(
    () => getCompletedTurnsCount(selectedRunId, newRunTurns, fallbackTurns),
    [selectedRunId, newRunTurns, fallbackTurns],
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
