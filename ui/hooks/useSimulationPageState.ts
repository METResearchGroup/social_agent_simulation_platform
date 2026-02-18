'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import { ApiError, Run, RunConfig, Turn } from '@/types';

const EMPTY_RUN_CONFIGS: Record<string, RunConfig> = {};
const EMPTY_NEW_RUN_TURNS: Record<string, Record<string, Turn>> = {};
const EMPTY_FALLBACK_TURNS: Record<string, Record<string, Turn>> = {};
const TURN_FETCH_THROTTLE_MS: number = 1500;

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
  /** Error from the last turns fetch attempt for the selected run. Cleared on success or retry. */
  turnsError: ApiError | null;
  /** Retries loading turns for a run. Clears error and triggers re-fetch immediately (bypasses throttle). */
  retryTurns: (runId: string) => void;
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
  const turnsFetchInFlightRef = useRef<Set<string>>(new Set());
  const lastTurnsFetchAttemptAtMsRef = useRef<Map<string, number>>(new Map());
  const loadedTurnsRunIdsRef = useRef<Set<string>>(new Set());
  const [turnsError, setTurnsError] = useState<ApiError | null>(null);
  const [turnsRetryTrigger, setTurnsRetryTrigger] = useState<number>(0);

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

  /**
   * Loads turns for the selected run. On failure, sets turnsError (run is not marked loaded).
   * User can retry via retryTurns(runId) or by reselecting the run after 1.5s (throttle window).
   */
  useEffect(() => {
    if (!selectedRunId || loadedTurnsRunIdsRef.current.has(selectedRunId)) {
      if (selectedRunId) {
        setTurnsError(null);
      }
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
    setTurnsError(null);

    const loadTurnsForRun = async (): Promise<void> => {
      try {
        const turnsForRun: Record<string, Turn> = await getTurnsForRun(runId);
        loadedTurnsRunIdsRef.current.add(runId);
        if (isMounted) {
          setTurnsError(null);
          setFallbackTurns((previousTurns) => ({
            ...previousTurns,
            [runId]: turnsForRun,
          }));
        }
      } catch (error) {
        if (isMounted && runId === selectedRunId) {
          setTurnsError(error instanceof ApiError ? error : new ApiError('UNKNOWN_ERROR', String(error), null, 0));
        }
        console.error(`Failed to fetch turns for ${runId}:`, error);
      } finally {
        turnsFetchInFlightRef.current.delete(runId);
      }
    };

    void loadTurnsForRun();

    return () => {
      isMounted = false;
    };
  }, [selectedRunId, turnsRetryTrigger]);

  const retryTurns = useCallback((runId: string) => {
    loadedTurnsRunIdsRef.current.delete(runId);
    lastTurnsFetchAttemptAtMsRef.current.delete(runId);
    setTurnsError(null);
    setTurnsRetryTrigger((t) => t + 1);
  }, []);

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
    turnsError,
    retryTurns,
    handleConfigSubmit,
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
  };
}
