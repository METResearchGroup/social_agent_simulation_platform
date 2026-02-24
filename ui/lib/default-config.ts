import type { RunConfig } from '@/types';

/** Fallback when GET /simulations/config/default fails. */
export const FALLBACK_DEFAULT_CONFIG: RunConfig = {
  numAgents: 5,
  numTurns: 10,
  feedAlgorithm: 'chronological',
  feedAlgorithmConfig: null,
  metricKeys: undefined,
};
