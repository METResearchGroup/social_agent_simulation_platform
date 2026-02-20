'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  getAgents,
  getRuns,
  getTurnsForRun,
  postRun,
} from '@/lib/api/simulation';
import {
  getAvailableTurns,
  getCompletedTurnsCount,
  getCurrentTurn,
  getRunAgents,
  getRunConfig,
  withComputedRunStatuses,
} from '@/lib/run-selectors';
import { ApiError, Agent, Run, RunConfig, Turn } from '@/types';

const EMPTY_RUN_CONFIGS: Record<string, RunConfig> = {};
const EMPTY_NEW_RUN_TURNS: Record<string, Record<string, Turn>> = {};
const EMPTY_FALLBACK_TURNS: Record<string, Record<string, Turn>> = {};
const EMPTY_TURNS_LOADING: Record<string, boolean> = {};
const EMPTY_TURNS_ERROR: Record<string, ApiError | null> = {};
const TURN_FETCH_THROTTLE_MS: number = 1500;

/**
 * Result of useSimulationPageState.
 *
 * Loading/error contract:
 * - runsLoading: true while getRuns() is in flight; false otherwise.
 * - runsError: set when runs fetch fails; cleared when handleRetryRuns is called.
 * - agentsLoading: true while getAgents() is in flight; false otherwise.
 * - agentsError: set when agents fetch fails; cleared when handleRetryAgents is called.
 * - turnsLoadingByRunId: runId -> true while turns for that run are loading.
 * - turnsErrorByRunId: runId -> Error when turns fetch fails; cleared when handleRetryTurns(runId) is called.
 */
interface UseSimulationPageStateResult {
  runsWithStatus: Run[];
  runsLoading: boolean;
  runsError: Error | null;
  agentsLoading: boolean;
  agentsError: Error | null;
  turnsLoadingByRunId: Record<string, boolean>;
  turnsErrorByRunId: Record<string, ApiError | null>;
  selectedRunId: string | null;
  selectedTurn: number | 'summary' | null;
  selectedRun: Run | null;
  currentTurn: Turn | null;
  availableTurns: number[];
  completedTurnsCount: number;
  runAgents: Agent[];
  currentRunConfig: RunConfig | null;
  isStartScreen: boolean;
  handleConfigSubmit: (config: RunConfig) => void;
  handleSelectRun: (runId: string) => void;
  handleSelectTurn: (turn: number | 'summary') => void;
  handleStartNewRun: () => void;
  handleRetryRuns: () => void;
  handleRetryAgents: () => void;
  handleRetryTurns: (runId: string) => void;
}

export function useSimulationPageState(): UseSimulationPageStateResult {
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState<boolean>(true);
  const [runsError, setRunsError] = useState<Error | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState<boolean>(true);
  const [agentsError, setAgentsError] = useState<Error | null>(null);
  const [retryAgentsTrigger, setRetryAgentsTrigger] = useState<number>(0);
  const [turnsLoadingByRunId, setTurnsLoadingByRunId] = useState<Record<string, boolean>>(
    EMPTY_TURNS_LOADING,
  );
  const [turnsErrorByRunId, setTurnsErrorByRunId] = useState<Record<string, ApiError | null>>(
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
  const agentsRequestIdRef = useRef<number>(0);

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

  /**
   * Loads turns for the selected run. On failure, sets turnsError (run is not marked loaded).
   * User can retry via retryTurns(runId) or by reselecting the run after 1.5s (throttle window).
   */
  useEffect(() => {
    let isMounted: boolean = true;
    agentsRequestIdRef.current += 1;
    const requestId: number = agentsRequestIdRef.current;
    setAgentsLoading(true);
    setAgentsError(null);

    const loadAgents = async (): Promise<void> => {
      try {
        const apiAgents: Agent[] = await getAgents();
        if (!isMounted || requestId !== agentsRequestIdRef.current) return;
        setAgents(apiAgents);
      } catch (error: unknown) {
        console.error('Failed to fetch agents:', error);
        if (!isMounted || requestId !== agentsRequestIdRef.current) return;
        setAgentsError(error instanceof Error ? error : new Error(String(error)));
      } finally {
        if (!isMounted || requestId !== agentsRequestIdRef.current) return;
        setAgentsLoading(false);
      }
    };

    void loadAgents();

    return () => {
      isMounted = false;
    };
  }, [retryAgentsTrigger]);

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
          const apiError: ApiError =
            error instanceof ApiError ? error : new ApiError('UNKNOWN_ERROR', String(error), null, 0);
          setTurnsErrorByRunId((prev) => ({ ...prev, [runId]: apiError }));
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
    () => getRunAgents(selectedRun, agents),
    [selectedRun, agents],
  );

  const currentRunConfig: RunConfig | null = useMemo(
    () => getRunConfig(selectedRun, runConfigs),
    [selectedRun, runConfigs],
  );

  const handleConfigSubmit = (config: RunConfig): void => {
    setRunsError(null); // Clear stale run errors before starting a new run.
    void postRun(config)
      .then((newRun) => {
        setRuns((previousRuns) => [newRun, ...previousRuns]);
        setRunConfigs((previousConfigs) => ({
          ...previousConfigs,
          [newRun.runId]: config,
        }));
        setSelectedRunId(newRun.runId);
        setSelectedTurn('summary');
      })
      .catch((error: unknown) => {
        console.error('Failed to start simulation:', error);
        setRunsError(error instanceof Error ? error : new Error(String(error)));
      });
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

  const handleRetryAgents = (): void => {
    setAgentsError(null);
    setRetryAgentsTrigger((t) => t + 1);
  };

  const handleRetryTurns = (runId: string): void => {
    setTurnsErrorByRunId((prev) => {
      const next: Record<string, ApiError | null> = { ...prev };
      delete next[runId];
      return next;
    });
    loadedTurnsRunIdsRef.current.delete(runId);
    lastTurnsFetchAttemptAtMsRef.current.delete(runId);
    setRetryTurnsTrigger((t) => t + 1);
  };

  return {
    runsWithStatus,
    runsLoading,
    runsError,
    agentsLoading,
    agentsError,
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
    handleRetryAgents,
    handleRetryTurns,
  };
}
