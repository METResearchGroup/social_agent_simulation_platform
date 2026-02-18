'use client';

import { RunConfig } from '@/types';

interface RunParametersBlockProps {
  config: RunConfig | null;
}

export default function RunParametersBlock({ config }: RunParametersBlockProps) {
  if (!config) {
    return null;
  }

  return (
    <div className="p-4 border-b border-beige-300 bg-beige-50">
      <h3 className="text-sm font-medium text-beige-900 mb-2">Run Parameters</h3>
      <div className="text-sm text-beige-700 space-y-1">
        <div>Agents: {config.numAgents}</div>
        <div>Turns: {config.numTurns}</div>
      </div>
    </div>
  );
}
