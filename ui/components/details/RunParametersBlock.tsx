'use client';

import { RunConfig } from '@/types';

interface RunParametersBlockProps {
  config: RunConfig | null;
}

export default function RunParametersBlock({ config }: RunParametersBlockProps) {
  if (!config) {
    return null;
  }

  const hasAlgorithmConfig: boolean = Object.keys(config.feedAlgorithmConfig).length > 0;

  return (
    <div className="p-4 border-b border-beige-300 bg-beige-50">
      <h3 className="text-sm font-medium text-beige-900 mb-2">Run Parameters</h3>
      <div className="text-sm text-beige-700 space-y-1">
        <div>Agents: {config.numAgents}</div>
        <div>Turns: {config.numTurns}</div>
        <div>Feed Algorithm: {config.feedAlgorithm}</div>
        {hasAlgorithmConfig ? (
          <pre className="mt-2 whitespace-pre-wrap rounded bg-beige-100 p-2 text-xs text-beige-800">
            {JSON.stringify(config.feedAlgorithmConfig, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}
