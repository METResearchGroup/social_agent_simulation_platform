'use client';

import { useState } from 'react';
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
  const parts = [
    metric.description,
    `Scope: ${metric.scope}`,
    `Author: ${metric.author}`,
    metric.key !== metric.displayName ? `Key: ${metric.key}` : null,
  ];
  return parts.filter(Boolean).join('\n');
}

interface MetricCardGridProps {
  metrics: Metric[];
  selectedKeys: string[];
  onToggleKey: (key: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
  disabled: boolean;
}

function MetricCardGrid({
  metrics,
  selectedKeys,
  onToggleKey,
  onSelectAll,
  onClearAll,
  disabled,
}: MetricCardGridProps) {
  const selectedSet = new Set(selectedKeys);
  if (metrics.length === 0) return null;

  return (
    <div className="mt-2">
      <div className="flex justify-end gap-2 mb-2">
        <button
          type="button"
          onClick={onSelectAll}
          disabled={disabled}
          className="text-xs text-beige-600 hover:text-beige-800 disabled:opacity-50"
        >
          Select all
        </button>
        <button
          type="button"
          onClick={onClearAll}
          disabled={disabled}
          className="text-xs text-beige-600 hover:text-beige-800 disabled:opacity-50"
        >
          Clear
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {metrics.map((metric) => {
          const isSelected = selectedSet.has(metric.key);
          return (
            <button
              key={metric.key}
              type="button"
              title={buildTooltip(metric)}
              onClick={() => onToggleKey(metric.key)}
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
              <div className="font-medium break-words">{metric.displayName}</div>
              <div className="text-xs text-beige-600 mt-0.5">
                Scope: {metric.scope}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface ScopeSectionProps {
  title: string;
  metrics: Metric[];
  selectedKeys: string[];
  expanded: boolean;
  onToggleExpand: () => void;
  onSelectionChange: (keys: string[]) => void;
  disabled: boolean;
}

function ScopeSection({
  title,
  metrics,
  selectedKeys,
  expanded,
  onToggleExpand,
  onSelectionChange,
  disabled,
}: ScopeSectionProps) {
  const selectedSet = new Set(selectedKeys);
  const scopeKeys = metrics.map((m) => m.key);

  const toggleKey = (key: string): void => {
    if (selectedSet.has(key)) {
      onSelectionChange(selectedKeys.filter((k) => k !== key));
    } else {
      onSelectionChange([...selectedKeys, key].sort());
    }
  };

  const selectAll = (): void => {
    const next = new Set(selectedKeys);
    scopeKeys.forEach((k) => next.add(k));
    onSelectionChange([...next].sort());
  };

  const clearAll = (): void => {
    const next = selectedKeys.filter((k) => !scopeKeys.includes(k));
    onSelectionChange(next);
  };

  if (metrics.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={onToggleExpand}
        className="text-sm font-medium text-beige-800 hover:text-beige-900 transition-colors"
      >
        {expanded ? '▾' : '▸'} {title}
      </button>
      {expanded && (
        <div className="mt-2 ml-3 pl-4 border-l border-beige-200">
          <MetricCardGrid
            metrics={metrics}
            selectedKeys={selectedKeys}
            onToggleKey={toggleKey}
            onSelectAll={selectAll}
            onClearAll={clearAll}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  );
}

export default function MetricSelector({
  metrics,
  selectedKeys,
  onSelectionChange,
  showMetricsSection,
  onToggleShowMetricsSection,
  disabled = false,
}: MetricSelectorProps) {
  const [showTurn, setShowTurn] = useState(true);
  const [showRun, setShowRun] = useState(true);

  const turnMetrics = metrics.filter((m) => m.scope === 'turn');
  const runMetrics = metrics.filter((m) => m.scope === 'run');

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
          <p className="text-sm text-beige-600 mb-2">
            Choose which metrics to track for this run. Click a card to toggle.
          </p>
          <ScopeSection
            title="Turn-level metrics"
            metrics={turnMetrics}
            selectedKeys={selectedKeys}
            expanded={showTurn}
            onToggleExpand={() => setShowTurn((v) => !v)}
            onSelectionChange={onSelectionChange}
            disabled={disabled}
          />
          <ScopeSection
            title="Run-level metrics"
            metrics={runMetrics}
            selectedKeys={selectedKeys}
            expanded={showRun}
            onToggleExpand={() => setShowRun((v) => !v)}
            onSelectionChange={onSelectionChange}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  );
}
