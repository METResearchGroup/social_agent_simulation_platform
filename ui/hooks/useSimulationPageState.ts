'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
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
const EMPTY_TURNS_LOADING: Record<string, boolean> = {};
const EMPTY_TURNS_ERROR: Record<string, Error | null> = {};
const TURN_FETCH_THROTTLE_MS: number = 1500;

/**
 * Result of useSimulationPageState.
 *
 * Loading/error contract:
 * - runsLoading: true while getRuns() is in flight; false otherwise.
 * - runsError: set when runs fetch fails; cleared when handleRetryRuns is called.
 * - turnsLoadingByRunId: runId -> true while turns for that run are loading.
 * - turnsErrorByRunId: runId -> Error when turns fetch fails; cleared when handleRetryTurns(runId) is called.
 */
interface UseSimulationPageStateResult {
  runsWithStatus: Run[];
  runsLoading: boolean;
  runsError: Error | null;
  turnsLoadingByRunId: Record<string, boolean>;
  turnsErrorByRunId: Record<string, Error | null>;
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
  handleRetryRuns: () => void;
  handleRetryTurns: (runId: string) => void;
}

export function useSimulationPageState(): UseSimulationPageStateResult {
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState<boolean>(true);
  const [runsError, setRunsError] = useState<Error | null>(null);
  const [turnsLoadingByRunId, setTurnsLoadingByRunId] = useState<Record<string, boolean>>(
    EMPTY_TURNS_LOADING,
  );
  const [turnsErrorByRunId, setTurnsErrorByRunId] = useState<Record<string, Error | null>>(
    EMPTY_TURNS_ERROR,
  );
  const [retryRunsTrigger, setRetryRunsTrigger] = useState<number>(0);
  const [retryTurnsTrigger, setRetryTurnsTrigger] = useState<number>(0);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedTurn, setSelectedTurn] = useState<number | 'summary' | null>(null);
  const [runConfigs, setRunConfigs] = useState<Record<string, RunConfig>>(EMPTY_RUN_CONFIGS);
  const [newRunTurns] = useState<Record<string, Record<string, Turn>>>(EMPTY_NEW_RUN_TURNS);
  const [fallbackTurns, setFallbackTurns] = useState<Record<string, Record<string, Turn>>>(
    EMPTY_FALLBACK_TURNS,
  );
  const turnsFetchInFlightRef = useRef<Set<string>>(new Set());
  const lastTurnsFetchAttemptAtMsRef = useRef<Map<string, number>>(new Map());
  const loadedTurnsRunIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let isMounted: boolean = true;
    setRunsLoading(true);
    setRunsError(null);

    const loadRuns = async (): Promise<void> => {
      try {
        const apiRuns: Run[] = await getRuns();
        if (isMounted) {
          setRuns(apiRuns);
        }
      } catch (error: unknown) {
        console.error('Failed to fetch runs:', error);
        if (isMounted) {
          setRunsError(error instanceof Error ? error : new Error(String(error)));
        }
      } finally {
        if (isMounted) {
          setRunsLoading(false);
        }
      }
    };

    void loadRuns();

    return () => {
      isMounted = false;
    };
  }, [retryRunsTrigger]);

  useEffect(() => {
    if (!selectedRunId || loadedTurnsRunIdsRef.current.has(selectedRunId)) {
      return;
    }

    const nowMs: number = Date.now();
    const lastAttemptMs: number = lastTurnsFetchAttemptAtMsRef.current.get(selectedRunId) ?? 0;
    if (nowMs - lastAttemptMs < TURN_FETCH_THROTTLE_MS) {
      return;
    }

    if (turnsFetchInFlightRef.current.has(selectedRunId)) {
      return;
    }

    let isMounted: boolean = true;
    const runId: string = selectedRunId;
    turnsFetchInFlightRef.current.add(runId);
    lastTurnsFetchAttemptAtMsRef.current.set(runId, nowMs);
    setTurnsLoadingByRunId((prev) => ({ ...prev, [runId]: true }));
    setTurnsErrorByRunId((prev) => ({ ...prev, [runId]: null }));

    const loadTurnsForRun = async (): Promise<void> => {
      try {
        const turnsForRun: Record<string, Turn> = await getTurnsForRun(runId);
        loadedTurnsRunIdsRef.current.add(runId);
        if (isMounted) {
          setFallbackTurns((previousTurns) => ({
            ...previousTurns,
            [runId]: turnsForRun,
          }));
        }
      } catch (error: unknown) {
        console.error(`Failed to fetch turns for ${runId}:`, error);
        if (isMounted) {
          setTurnsErrorByRunId((prev) => ({
            ...prev,
            [runId]: error instanceof Error ? error : new Error(String(error)),
          }));
        }
      } finally {
        turnsFetchInFlightRef.current.delete(runId);
        if (isMounted) {
          setTurnsLoadingByRunId((prev) => ({ ...prev, [runId]: false }));
        }
      }
    };

    void loadTurnsForRun();

    return () => {
      isMounted = false;
    };
  }, [selectedRunId, retryTurnsTrigger]);

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

  const handleRetryRuns = (): void => {
    setRunsError(null);
    setRetryRunsTrigger((t) => t + 1);
  };

  const handleRetryTurns = (runId: string): void => {
    setTurnsErrorByRunId((prev) => {
      const next: Record<string, Error | null> = { ...prev };
      delete next[runId];
      return next;
    });
    loadedTurnsRunIdsRef.current.delete(runId);
    setRetryTurnsTrigger((t) => t + 1);
  };

  return {
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
    isStartScreen: selectedRunId === null,
    handleConfigSubmit,
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
    handleRetryRuns,
    handleRetryTurns,
  };
}
