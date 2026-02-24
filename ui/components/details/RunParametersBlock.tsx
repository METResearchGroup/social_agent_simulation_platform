'use client';

import { RunConfig } from '@/types';

interface RunParametersBlockProps {
  config: RunConfig | null;
}

export default function RunParametersBlock({ config }: RunParametersBlockProps) {
  if (!config) {
    return null;
  }

  const configEntries = config.feedAlgorithmConfig
    ? Object.entries(config.feedAlgorithmConfig)
    : [];

  return (
    <div className="p-4 border-b border-beige-300 bg-beige-50">
      <h3 className="text-sm font-medium text-beige-900 mb-2">Run Parameters</h3>
      <div className="text-sm text-beige-700 space-y-1">
        <div>Agents: {config.numAgents}</div>
        <div>Turns: {config.numTurns}</div>
        <div>Algorithm: {config.feedAlgorithm}</div>
        {configEntries.length > 0 && (
          <div className="pt-1">
            <div className="text-beige-900">Algorithm Config:</div>
            <div className="pl-3">
              {configEntries.map(([key, value]) => (
                <div key={key}>
                  {key}: {typeof value === 'string' ? value : JSON.stringify(value)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
