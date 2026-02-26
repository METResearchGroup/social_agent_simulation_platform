'use client';

import { ApiError, RunConfig } from '@/types';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface RunParametersBlockProps {
  config: RunConfig | null;
  runDetailsLoading?: boolean;
  runDetailsError?: ApiError | null;
  onRetryRunDetails?: () => void;
}

function RunParametersLoading() {
  return (
    <div className="p-4 border-b border-beige-300 bg-beige-50">
      <h3 className="text-sm font-medium text-beige-900 mb-2">Run Parameters</h3>
      <div className="flex items-center gap-2 text-sm text-beige-600">
        <LoadingSpinner />
        <span>Loading run config…</span>
      </div>
    </div>
  );
}

interface RunParametersErrorProps {
  onRetryRunDetails?: () => void;
}

function RunParametersError({ onRetryRunDetails }: RunParametersErrorProps) {
  return (
    <div className="p-4 border-b border-beige-300 bg-beige-50">
      <h3 className="text-sm font-medium text-beige-900 mb-2">Run Parameters</h3>
      <div className="flex flex-col gap-2 text-sm text-beige-800">
        <p>Could not load run config.</p>
        {onRetryRunDetails && (
          <button
            type="button"
            onClick={onRetryRunDetails}
            className="self-start px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

interface AlgorithmConfigBlockProps {
  entries: [string, unknown][];
}

function AlgorithmConfigBlock({ entries }: AlgorithmConfigBlockProps) {
  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="pt-1">
      <div className="text-beige-900">Algorithm Config:</div>
      <div className="pl-3">
        {entries.map(([key, value]) => (
          <div key={key}>
            {key}: {typeof value === 'string' ? value : JSON.stringify(value)}
          </div>
        ))}
      </div>
    </div>
  );
}

interface MetricsBlockProps {
  /**
   * Selected metric keys for this run.
   * - `undefined`: use backend default metrics
   * - `[]`: no metrics selected
   * - `[...keys]`: selected metrics
   */
  metricKeys?: string[];
}

function MetricsBlock({ metricKeys }: MetricsBlockProps) {
  return (
    <div className="pt-1">
      <span className="text-beige-900">Metrics: </span>
      {metricKeys === undefined ? (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-beige-200 text-beige-800">
          Default
        </span>
      ) : metricKeys.length === 0 ? (
        <span className="text-beige-600">—</span>
      ) : (
        <span className="flex flex-wrap gap-1.5 mt-1">
          {metricKeys.map((key) => (
            <span
              key={key}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-beige-200 text-beige-800"
            >
              {key}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}

interface RunParametersContentProps {
  config: RunConfig;
}

function RunParametersContent({ config }: RunParametersContentProps) {
  const configEntries = config.feedAlgorithmConfig ? Object.entries(config.feedAlgorithmConfig) : [];

  return (
    <div className="p-4 border-b border-beige-300 bg-beige-50">
      <h3 className="text-sm font-medium text-beige-900 mb-2">Run Parameters</h3>
      <div className="text-sm text-beige-700 space-y-1">
        <div>Agents: {config.numAgents}</div>
        <div>Turns: {config.numTurns}</div>
        <div>Algorithm: {config.feedAlgorithm}</div>
        <AlgorithmConfigBlock entries={configEntries} />
        <MetricsBlock metricKeys={config.metricKeys} />
      </div>
    </div>
  );
}

export default function RunParametersBlock({
  config,
  runDetailsLoading = false,
  runDetailsError = null,
  onRetryRunDetails,
}: RunParametersBlockProps) {
  if (runDetailsLoading) {
    return <RunParametersLoading />;
  }

  if (runDetailsError) {
    return <RunParametersError onRetryRunDetails={onRetryRunDetails} />;
  }

  if (!config) {
    return null;
  }

  return <RunParametersContent config={config} />;
}
