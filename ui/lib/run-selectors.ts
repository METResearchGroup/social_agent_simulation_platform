import { Agent, Run, RunConfig, Turn } from '@/types';
import { FALLBACK_DEFAULT_CONFIG } from '@/lib/default-config';

const MAX_VISIBLE_RUN_AGENTS: number = 8;
const EMPTY_TURNS: Record<string, Turn> = {};

// we set completed and failed as terminal states because we compute all actual
// logic in the backend and the UI only needs to reflect the terminal states.
const TERMINAL_RUN_STATUSES: ReadonlySet<Run['status']> = new Set(['completed', 'failed']);

type TurnSource = Record<string, Record<string, Turn>>;

export function getTurnsForRun(
  runId: string | null,
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): Record<string, Turn> {
  if (!runId) {
    return EMPTY_TURNS;
  }

  // newRunTurns is reserved for live per-run updates; fallbackTurns is
  // backend-fetched cached turn data keyed by run.
  return newRunTurns[runId] || fallbackTurns[runId] || EMPTY_TURNS;
}

export function getAvailableTurns(
  runId: string | null,
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): number[] {
  const turnsById: Record<string, Turn> = getTurnsForRun(runId, newRunTurns, fallbackTurns);
  return Object.keys(turnsById)
    .map(Number)
    .sort((a, b) => a - b);
}

export function getCompletedTurnsCount(
  runId: string | null,
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): number {
  return getAvailableTurns(runId, newRunTurns, fallbackTurns).length;
}

export function getCurrentTurn(
  selectedRunId: string | null,
  selectedTurn: number | 'summary' | null,
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): Turn | null {
  if (!selectedRunId || typeof selectedTurn !== 'number') {
    return null;
  }

  const turnsById: Record<string, Turn> = getTurnsForRun(
    selectedRunId,
    newRunTurns,
    fallbackTurns,
  );
  return turnsById[selectedTurn.toString()] || null;
}

export function getRunAgents(run: Run | null, allAgents: Agent[]): Agent[] {
  if (!run) {
    return allAgents;
  }

  const maxAgents: number = Math.min(run.totalAgents, allAgents.length, MAX_VISIBLE_RUN_AGENTS);
  return allAgents.slice(0, maxAgents);
}

export function getRunConfig(
  run: Run | null,
  runConfigs: Record<string, RunConfig>,
): RunConfig | null {
  if (!run) {
    return null;
  }

  const savedConfig: RunConfig | undefined = runConfigs[run.runId];
  if (savedConfig) {
    return savedConfig;
  }

  return {
    numAgents: run.totalAgents,
    numTurns: run.totalTurns,
    feedAlgorithm: FALLBACK_DEFAULT_CONFIG.feedAlgorithm,
  };
}


/**
 * Returns the run status for display. Status is computed in the backend; we
 * only check the run's status here and, if it is not terminal (e.g. completed
 * or failed), we treat it as running.
 */
export function getRunStatus(
  run: Run | null
): 'running' | 'completed' | 'failed' {
  if (!run) {
    return 'running';
  }

  if (TERMINAL_RUN_STATUSES.has(run.status)) {
    return run.status;
  }

  return 'running';
}

export function withComputedRunStatuses(runs: Run[]): Run[] {
  return runs.map((run) => ({
    ...run,
    status: getRunStatus(run),
  }));
}
