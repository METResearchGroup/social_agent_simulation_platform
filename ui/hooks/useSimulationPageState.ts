'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  getAgents,
  getMockAgents,
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
import { DEFAULT_AGENT_PAGE_SIZE } from '@/lib/constants';
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
 * - agentsLoadingMore: true while loading a subsequent agent page.
 * - mockAgentsLoading: true while getMockAgents() is in flight; false otherwise.
 * - mockAgentsError: set when mock agents fetch fails; cleared when handleRetryMockAgents is called.
 * - turnsLoadingByRunId: runId -> true while turns for that run are loading.
 * - turnsErrorByRunId: runId -> Error when turns fetch fails; cleared when handleRetryTurns(runId) is called.
 */
export type ViewMode = 'runs' | 'agents' | 'create-agent';

interface UseSimulationPageStateResult {
  runsWithStatus: Run[];
  runsLoading: boolean;
  runsError: Error | null;
  agents: Agent[];
  agentsLoading: boolean;
  agentsLoadingMore: boolean;
  agentsError: Error | null;
  agentsHasMore: boolean;
  mockAgents: Agent[];
  mockAgentsLoading: boolean;
  mockAgentsError: Error | null;
  turnsLoadingByRunId: Record<string, boolean>;
  turnsErrorByRunId: Record<string, ApiError | null>;
  viewMode: ViewMode;
  selectedAgentHandle: string | null;
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
  handleSetViewMode: (mode: ViewMode) => void;
  handleSelectAgent: (handle: string | null) => void;
  handleSelectRun: (runId: string) => void;
  handleSelectTurn: (turn: number | 'summary') => void;
  handleStartNewRun: () => void;
  handleRetryRuns: () => void;
  handleRetryAgents: () => void;
  handleLoadMoreAgents: () => void;
  handleRetryMockAgents: () => void;
  handleRetryTurns: (runId: string) => void;
}

export function useSimulationPageState(): UseSimulationPageStateResult {
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState<boolean>(true);
  const [runsError, setRunsError] = useState<Error | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState<boolean>(true);
  const [agentsLoadingMore, setAgentsLoadingMore] = useState<boolean>(false);
  const [agentsError, setAgentsError] = useState<Error | null>(null);
  const [retryAgentsTrigger, setRetryAgentsTrigger] = useState<number>(0);
  const [agentsHasMore, setAgentsHasMore] = useState<boolean>(false);
  const [agentsOffset, setAgentsOffset] = useState<number>(0);
  const [mockAgents, setMockAgents] = useState<Agent[]>([]);
  const [mockAgentsLoading, setMockAgentsLoading] = useState<boolean>(true);
  const [mockAgentsError, setMockAgentsError] = useState<Error | null>(null);
  const [retryMockAgentsTrigger, setRetryMockAgentsTrigger] = useState<number>(0);
  const [turnsLoadingByRunId, setTurnsLoadingByRunId] = useState<Record<string, boolean>>(
    EMPTY_TURNS_LOADING,
  );
  const [turnsErrorByRunId, setTurnsErrorByRunId] = useState<Record<string, ApiError | null>>(
    EMPTY_TURNS_ERROR,
  );
  const [retryRunsTrigger, setRetryRunsTrigger] = useState<number>(0);
  const [retryTurnsTrigger, setRetryTurnsTrigger] = useState<number>(0);
  const [viewMode, setViewMode] = useState<ViewMode>('runs');
  const [selectedAgentHandle, setSelectedAgentHandle] = useState<string | null>(null);
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
  const agentsLoadMoreRequestIdRef = useRef<number>(0);
  const mockAgentsRequestIdRef = useRef<number>(0);
  const runsRequestIdRef = useRef<number>(0);
  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let isMounted: boolean = true;
    runsRequestIdRef.current += 1;
    const requestId: number = runsRequestIdRef.current;
    setRunsLoading(true);
    setRunsError(null);

    const loadRuns = async (): Promise<void> => {
      try {
        const apiRuns: Run[] = await getRuns();
        if (!isMounted || requestId !== runsRequestIdRef.current) return;
        setRuns(apiRuns);
      } catch (error: unknown) {
        console.error('Failed to fetch runs:', error);
        if (!isMounted || requestId !== runsRequestIdRef.current) return;
        setRunsError(error instanceof Error ? error : new Error(String(error)));
      } finally {
        if (!isMounted || requestId !== runsRequestIdRef.current) return;
        setRunsLoading(false);
      }
    };

    void loadRuns();

    return () => {
      isMounted = false;
    };
  }, [retryRunsTrigger]);

  useEffect(() => {
    let isMounted: boolean = true;
    agentsRequestIdRef.current += 1;
    const requestId: number = agentsRequestIdRef.current;
    setAgentsLoading(true);
    setAgentsError(null);
    setAgentsHasMore(false);
    setAgentsOffset(0);
    setAgentsLoadingMore(false);

    const loadAgents = async (): Promise<void> => {
      try {
        const apiAgents: Agent[] = await getAgents({
          limit: DEFAULT_AGENT_PAGE_SIZE,
          offset: 0,
        });
        if (!isMounted || requestId !== agentsRequestIdRef.current) return;
        setAgents(apiAgents);
        setAgentsOffset(apiAgents.length);
        setAgentsHasMore(apiAgents.length === DEFAULT_AGENT_PAGE_SIZE);
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
    let isMounted: boolean = true;
    mockAgentsRequestIdRef.current += 1;
    const requestId: number = mockAgentsRequestIdRef.current;
    setMockAgentsLoading(true);
    setMockAgentsError(null);

    const loadMockAgents = async (): Promise<void> => {
      try {
        const apiMockAgents: Agent[] = await getMockAgents();
        if (!isMounted || requestId !== mockAgentsRequestIdRef.current) return;
        setMockAgents(apiMockAgents);
      } catch (error: unknown) {
        console.error('Failed to fetch mock agents:', error);
        if (!isMounted || requestId !== mockAgentsRequestIdRef.current) return;
        setMockAgentsError(error instanceof Error ? error : new Error(String(error)));
      } finally {
        if (isMounted && requestId === mockAgentsRequestIdRef.current) {
          setMockAgentsLoading(false);
        }
      }
    };

    void loadMockAgents();

    return () => {
      isMounted = false;
    };
  }, [retryMockAgentsTrigger]);

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
    () => getRunAgents(selectedRun, mockAgents),
    [selectedRun, mockAgents],
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

  const handleLoadMoreAgents = useCallback((): void => {
    if (agentsLoading || agentsLoadingMore || !agentsHasMore) {
      return;
    }

    agentsLoadMoreRequestIdRef.current += 1;
    const requestId: number = agentsLoadMoreRequestIdRef.current;
    setAgentsLoadingMore(true);
    setAgentsError(null);

    const loadMore = async (): Promise<void> => {
      try {
        const nextPage: Agent[] = await getAgents({
          limit: DEFAULT_AGENT_PAGE_SIZE,
          offset: agentsOffset,
        });
        if (!isMountedRef.current || requestId !== agentsLoadMoreRequestIdRef.current) {
          return;
        }
        setAgents((prev) => [...prev, ...nextPage]);
        setAgentsOffset((prev) => prev + nextPage.length);
        setAgentsHasMore(nextPage.length === DEFAULT_AGENT_PAGE_SIZE);
      } catch (error: unknown) {
        console.error('Failed to load more agents:', error);
        if (!isMountedRef.current) return;
        setAgentsError(error instanceof Error ? error : new Error(String(error)));
      } finally {
        if (isMountedRef.current && requestId === agentsLoadMoreRequestIdRef.current) {
          setAgentsLoadingMore(false);
        }
      }
    };

    void loadMore();
  }, [agentsHasMore, agentsLoading, agentsLoadingMore, agentsOffset]);

  const handleRetryMockAgents = (): void => {
    setMockAgentsError(null);
    setRetryMockAgentsTrigger((t) => t + 1);
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

  const handleSetViewMode = (mode: ViewMode): void => {
    setViewMode(mode);
    if (mode === 'create-agent') {
      setSelectedAgentHandle(null);
    }
  };

  const handleSelectAgent = (handle: string | null): void => {
    setSelectedAgentHandle(handle);
  };

  return {
    runsWithStatus,
    runsLoading,
    runsError,
    agents,
    agentsLoading,
    agentsLoadingMore,
    agentsError,
    agentsHasMore,
    mockAgents,
    mockAgentsLoading,
    mockAgentsError,
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
    isStartScreen: selectedRunId === null,
    handleConfigSubmit,
    handleSetViewMode,
    handleSelectAgent,
    handleSelectRun,
    handleSelectTurn,
    handleStartNewRun,
    handleRetryRuns,
    handleRetryAgents,
    handleLoadMoreAgents,
    handleRetryMockAgents,
    handleRetryTurns,
  };
}
