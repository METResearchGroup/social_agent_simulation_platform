'use client';

import { createContext, useContext } from 'react';
import { Agent, ApiError, Run, RunConfig, Turn } from '@/types';

interface RunDetailContextValue {
  selectedRun: Run | null;
  currentTurn: Turn | null;
  selectedTurn: number | 'summary' | null;
  availableTurns: number[];
  currentRunConfig: RunConfig | null;
  runAgents: Agent[];
  completedTurnsCount: number;
  turnsLoading: boolean;
  turnsError: ApiError | null;
  runDetailsLoading: boolean;
  runDetailsError: ApiError | null;
  onSelectTurn: (turn: number | 'summary') => void;
  onRetryTurns: () => void;
  onRetryRunDetails: () => void;
}

interface RunDetailProviderProps {
  value: RunDetailContextValue;
  children: React.ReactNode;
}

const RunDetailContext = createContext<RunDetailContextValue | null>(null);

export function RunDetailProvider({ value, children }: RunDetailProviderProps) {
  return <RunDetailContext.Provider value={value}>{children}</RunDetailContext.Provider>;
}

export function useRunDetail(): RunDetailContextValue {
  const contextValue: RunDetailContextValue | null = useContext(RunDetailContext);
  if (!contextValue) {
    throw new Error('useRunDetail must be used within RunDetailProvider');
  }
  return contextValue;
}
