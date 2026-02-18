import { Agent, Run, RunConfig, Turn } from '@/types';

const MAX_VISIBLE_RUN_AGENTS: number = 8;
const EMPTY_TURNS: Record<string, Turn> = {};

type TurnSource = Record<string, Record<string, Turn>>;

export function getTurnsForRun(
  runId: string | null,
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): Record<string, Turn> {
  if (!runId) {
    return EMPTY_TURNS;
  }

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
  };
}

export function getRunStatus(
  run: Run | null,
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): 'running' | 'completed' | 'failed' {
  if (!run) {
    return 'running';
  }

  const completedTurns: number = getCompletedTurnsCount(run.runId, newRunTurns, fallbackTurns);
  return completedTurns >= run.totalTurns ? 'completed' : 'running';
}

export function withComputedRunStatuses(
  runs: Run[],
  newRunTurns: TurnSource,
  fallbackTurns: TurnSource,
): Run[] {
  return runs.map((run) => ({
    ...run,
    status: getRunStatus(run, newRunTurns, fallbackTurns),
  }));
}
