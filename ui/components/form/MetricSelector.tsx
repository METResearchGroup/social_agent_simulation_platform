'use client';

import type { Metric } from '@/types';

interface MetricSelectorProps {
  metrics: Metric[];
  selectedKeys: string[];
  onSelectionChange: (keys: string[]) => void;
  showMetricsSection: boolean;
  onToggleShowMetricsSection: () => void;
  disabled?: boolean;
}

function buildTooltip(metric: Metric): string {
  const parts = [metric.description, `Scope: ${metric.scope}`, `Author: ${metric.author}`];
  return parts.filter(Boolean).join('\n');
}

export default function MetricSelector({
  metrics,
  selectedKeys,
  onSelectionChange,
  showMetricsSection,
  onToggleShowMetricsSection,
  disabled = false,
}: MetricSelectorProps) {
  const selectedSet = new Set(selectedKeys);

  const toggleKey = (key: string): void => {
    if (disabled) return;
    if (selectedSet.has(key)) {
      onSelectionChange(selectedKeys.filter((k) => k !== key));
    } else {
      onSelectionChange([...selectedKeys, key].sort());
    }
  };

  const selectAll = (): void => {
    if (disabled) return;
    onSelectionChange(metrics.map((m) => m.key).sort());
  };

  const clearAll = (): void => {
    if (disabled) return;
    onSelectionChange([]);
  };

  if (metrics.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <button
          type="button"
          aria-expanded={showMetricsSection}
          onClick={onToggleShowMetricsSection}
          className="text-sm font-medium text-beige-800 hover:text-beige-900 transition-colors"
        >
          {showMetricsSection ? '▾' : '▸'} Metrics
        </button>
        {showMetricsSection && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={selectAll}
              disabled={disabled}
              className="text-xs text-beige-600 hover:text-beige-800 disabled:opacity-50"
            >
              Select all
            </button>
            <button
              type="button"
              onClick={clearAll}
              disabled={disabled}
              className="text-xs text-beige-600 hover:text-beige-800 disabled:opacity-50"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {showMetricsSection && (
        <div className="mt-3 ml-3 pl-4 border-l border-beige-200">
          <p className="text-sm text-beige-600 mb-3">
            Choose which metrics to track for this run. Click a card to toggle.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {metrics.map((metric) => {
              const isSelected = selectedSet.has(metric.key);
              return (
                <button
                  key={metric.key}
                  type="button"
                  title={buildTooltip(metric)}
                  onClick={() => toggleKey(metric.key)}
                  disabled={disabled}
                  className={`
                    text-left px-3 py-2 rounded-lg border text-sm transition-colors
                    focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${
                      isSelected
                        ? 'border-accent bg-accent/10 text-beige-900'
                        : 'border-beige-300 bg-white text-beige-800 hover:border-beige-400 hover:bg-beige-50'
                    }
                  `}
                >
                  <span className="font-medium break-words" title={metric.key}>
                    {metric.key}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
