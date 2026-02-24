'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import AlgorithmSettingsSection from '@/components/form/AlgorithmSettingsSection';
import {
  buildDefaults,
  normalizeConfigSchema,
  pruneConfig,
  validateConfig,
} from '@/components/form/config-schema';
import type { JsonObject } from '@/components/form/config-schema';
import { getAvailableMetrics, getFeedAlgorithms } from '@/lib/api/simulation';
import { FeedAlgorithm, Metric, RunConfig } from '@/types';
import MetricSelector from '@/components/form/MetricSelector';

interface ConfigFormProps {
  onSubmit: (config: RunConfig) => void;
  defaultConfig: RunConfig;
}

export default function ConfigForm({ onSubmit, defaultConfig }: ConfigFormProps) {
  const [numAgents, setNumAgents] = useState(defaultConfig.numAgents);
  const [numTurns, setNumTurns] = useState(defaultConfig.numTurns);
  const [feedAlgorithm, setFeedAlgorithm] = useState<string>(defaultConfig.feedAlgorithm);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [showAlgorithmSettings, setShowAlgorithmSettings] = useState(false);
  const [feedAlgorithmConfigByAlgId, setFeedAlgorithmConfigByAlgId] = useState<
    Record<string, JsonObject>
  >(() =>
    defaultConfig.feedAlgorithmConfig
      ? { [defaultConfig.feedAlgorithm]: defaultConfig.feedAlgorithmConfig }
      : {},
  );
  const [feedAlgorithmConfig, setFeedAlgorithmConfig] = useState<JsonObject>(
    defaultConfig.feedAlgorithmConfig || {},
  );
  const [algorithms, setAlgorithms] = useState<FeedAlgorithm[]>([]);
  const algorithmsRequestIdRef = useRef<number>(0);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [selectedMetricKeys, setSelectedMetricKeys] = useState<string[]>(
    defaultConfig.metricKeys && defaultConfig.metricKeys.length > 0 ? defaultConfig.metricKeys : [],
  );
  const [showMetricsSection, setShowMetricsSection] = useState(true);
  const metricsRequestIdRef = useRef<number>(0);

  useEffect(() => {
    let isMounted = true;
    algorithmsRequestIdRef.current += 1;
    const requestId = algorithmsRequestIdRef.current;

    const load = async (): Promise<void> => {
      try {
        const list = await getFeedAlgorithms();
        if (!isMounted || requestId !== algorithmsRequestIdRef.current) return;
        if (list.length === 0) {
          console.warn(
            '[ConfigForm] Feed algorithms empty or failed to load; showing fallback. Check GET /simulations/feed-algorithms.',
          );
        }
        setAlgorithms(list);
      } catch (err) {
        console.error('Failed to fetch feed algorithms:', err);
      }
    };

    void load();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    metricsRequestIdRef.current += 1;
    const requestId = metricsRequestIdRef.current;

    const load = async (): Promise<void> => {
      try {
        const list = await getAvailableMetrics();
        if (!isMounted || requestId !== metricsRequestIdRef.current) return;
        if (list.length === 0) {
          console.warn(
            '[ConfigForm] Metrics list empty or failed to load; metric selector hidden.',
          );
        }
        setMetrics(list);
        setSelectedMetricKeys((prev) => {
          if (prev.length > 0) return prev;
          return list.map((m) => m.key).sort();
        });
      } catch (err) {
        console.error('Failed to fetch metrics:', err);
      }
    };

    void load();
    return () => {
      isMounted = false;
    };
  }, []);

  const selectedAlg = algorithms.find((a) => a.id === feedAlgorithm);
  const normalizedSchema = useMemo(
    () => normalizeConfigSchema(selectedAlg?.configSchema ?? null),
    [selectedAlg?.configSchema],
  );
  const schemaFields = useMemo(() => normalizedSchema?.fields ?? [], [normalizedSchema]);
  const configErrors = useMemo(
    () => validateConfig(schemaFields, feedAlgorithmConfig),
    [schemaFields, feedAlgorithmConfig],
  );

  useEffect(() => {
    setShowAlgorithmSettings(schemaFields.length > 0);
  }, [schemaFields.length]);

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (Object.keys(configErrors).length > 0) {
      setSubmitAttempted(true);
      return;
    }

    onSubmit({
      numAgents,
      numTurns,
      feedAlgorithm,
      feedAlgorithmConfig: pruneConfig(feedAlgorithmConfig),
      metricKeys: selectedMetricKeys.length > 0 ? selectedMetricKeys : undefined,
    });
  };

  useEffect(() => {
    setSubmitAttempted(false);
    const saved = feedAlgorithmConfigByAlgId[feedAlgorithm];
    if (saved) {
      setFeedAlgorithmConfig(saved);
      return;
    }

    const defaults = buildDefaults(schemaFields);
    setFeedAlgorithmConfig(defaults);
    if (Object.keys(defaults).length > 0) {
      setFeedAlgorithmConfigByAlgId((prev) => ({ ...prev, [feedAlgorithm]: defaults }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedAlgorithm, selectedAlg?.configSchema]);

  const setConfigValue = (key: string, value: unknown | undefined): void => {
    setFeedAlgorithmConfig((prev) => {
      const next: JsonObject = { ...prev };
      if (value === undefined) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return next;
    });
    setFeedAlgorithmConfigByAlgId((prev) => {
      const existing = prev[feedAlgorithm] || {};
      const next: JsonObject = { ...existing };
      if (value === undefined) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return { ...prev, [feedAlgorithm]: next };
    });
  };

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-beige-900 mb-8 text-center">
          Start New Simulation
        </h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="feedAlgorithm"
              className="block text-sm font-medium text-beige-800 mb-2"
            >
              Feed Algorithm
            </label>
            <select
              id="feedAlgorithm"
              value={feedAlgorithm}
              onChange={(e) => setFeedAlgorithm(e.target.value)}
              className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
            >
              {/* Fetch failures are caught in the useEffect above; check console for error/warning. TODO: switch to structured logging. */}
              {algorithms.length === 0 ? (
                <option value="chronological">Chronological</option>
              ) : (
                algorithms.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.displayName}
                  </option>
                ))
              )}
            </select>
            {selectedAlg?.description && (
              <p className="mt-1 text-sm text-beige-600">{selectedAlg.description}</p>
            )}
            <AlgorithmSettingsSection
              schemaFields={schemaFields}
              feedAlgorithmConfig={feedAlgorithmConfig}
              configErrors={configErrors}
              submitAttempted={submitAttempted}
              showAlgorithmSettings={showAlgorithmSettings}
              onToggleShowAlgorithmSettings={() => setShowAlgorithmSettings((v) => !v)}
              onSetConfigValue={setConfigValue}
            />
          </div>

          <div>
            <MetricSelector
              metrics={metrics}
              selectedKeys={selectedMetricKeys}
              onSelectionChange={setSelectedMetricKeys}
              showMetricsSection={showMetricsSection}
              onToggleShowMetricsSection={() => setShowMetricsSection((v) => !v)}
            />
          </div>

          <div>
            <label
              htmlFor="numAgents"
              className="block text-sm font-medium text-beige-800 mb-2"
            >
              Number of Agents
            </label>
            <input
              id="numAgents"
              type="number"
              min="1"
              max="20"
              value={numAgents}
              onChange={(event) => {
                const value: number = Number(event.currentTarget.value);
                setNumAgents(Number.isNaN(value) || value < 1 ? 1 : value);
              }}
              className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
              required
            />
          </div>
          <div>
            <label
              htmlFor="numTurns"
              className="block text-sm font-medium text-beige-800 mb-2"
            >
              Number of Turns
            </label>
            <input
              id="numTurns"
              type="number"
              min="1"
              max="100"
              value={numTurns}
              onChange={(event) => {
                const value: number = Number(event.currentTarget.value);
                setNumTurns(Number.isNaN(value) || value < 1 ? 1 : value);
              }}
              className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
              required
            />
          </div>
          <button
            type="submit"
            disabled={Object.keys(configErrors).length > 0}
            className="w-full px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent-hover transition-colors"
          >
            Start Simulation
          </button>
        </form>
      </div>
    </div>
  );
}
