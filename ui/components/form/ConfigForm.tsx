'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { getFeedAlgorithms } from '@/lib/api/simulation';
import { FeedAlgorithm, RunConfig } from '@/types';

interface ConfigFormProps {
  onSubmit: (config: RunConfig) => void;
  defaultConfig: RunConfig;
}

type JsonObject = Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

type NormalizedFieldKind = 'string' | 'string_enum' | 'number' | 'integer' | 'boolean' | 'unsupported';

interface NormalizedField {
  key: string;
  label: string;
  description: string | null;
  kind: NormalizedFieldKind;
  required: boolean;
  defaultValue?: unknown;
  minimum?: number;
  maximum?: number;
  enumValues?: string[];
}

interface NormalizedConfigSchema {
  fields: NormalizedField[];
}

function normalizeNullableSchema(schema: unknown): unknown {
  if (!isRecord(schema)) return schema;

  // type: ["string", "null"] (or other primitive + null)
  const type = schema.type;
  if (Array.isArray(type) && type.length === 2 && type.includes('null')) {
    const nonNull = type.find((t) => t !== 'null');
    if (typeof nonNull === 'string') {
      return { ...schema, type: nonNull };
    }
  }

  // anyOf: [{ type: <t> }, { type: "null" }]
  const anyOf = schema.anyOf;
  if (Array.isArray(anyOf) && anyOf.length === 2) {
    const types = anyOf
      .map((item) => (isRecord(item) ? item.type : null))
      .filter((t): t is string => typeof t === 'string');
    if (types.length === 2 && types.includes('null')) {
      const nonNull = types.find((t) => t !== 'null');
      const nonNullSchema = anyOf.find(
        (item) => isRecord(item) && item.type === nonNull,
      ) as unknown;
      return nonNullSchema ?? schema;
    }
  }

  return schema;
}

function normalizeConfigSchema(schema: unknown): NormalizedConfigSchema | null {
  if (!isRecord(schema)) return null;
  if (schema.type !== 'object') return null;

  const properties = schema.properties;
  if (!isRecord(properties)) return null;

  const requiredKeys = isStringArray(schema.required) ? new Set(schema.required) : new Set<string>();

  const fields: NormalizedField[] = Object.entries(properties).map(([key, raw]) => {
    const propSchema = normalizeNullableSchema(raw);
    const required = requiredKeys.has(key);

    if (!isRecord(propSchema)) {
      return {
        key,
        label: key,
        description: null,
        kind: 'unsupported',
        required,
      };
    }

    const title = typeof propSchema.title === 'string' ? propSchema.title : null;
    const description = typeof propSchema.description === 'string' ? propSchema.description : null;
    const type = propSchema.type;

    const base: Omit<NormalizedField, 'kind'> = {
      key,
      label: title || key,
      description,
      required,
    };

    if (type === 'string') {
      if (isStringArray(propSchema.enum)) {
        return {
          ...base,
          kind: 'string_enum',
          enumValues: propSchema.enum,
          defaultValue: typeof propSchema.default === 'string' ? propSchema.default : undefined,
        };
      }
      return {
        ...base,
        kind: 'string',
        defaultValue: typeof propSchema.default === 'string' ? propSchema.default : undefined,
      };
    }

    if (type === 'integer' || type === 'number') {
      const minimum = typeof propSchema.minimum === 'number' ? propSchema.minimum : undefined;
      const maximum = typeof propSchema.maximum === 'number' ? propSchema.maximum : undefined;
      const defaultValue = typeof propSchema.default === 'number' ? propSchema.default : undefined;
      return {
        ...base,
        kind: type,
        minimum,
        maximum,
        defaultValue,
      };
    }

    if (type === 'boolean') {
      const defaultValue = typeof propSchema.default === 'boolean' ? propSchema.default : undefined;
      return {
        ...base,
        kind: 'boolean',
        defaultValue,
      };
    }

    return {
      ...base,
      kind: 'unsupported',
    };
  });

  return { fields };
}

function buildDefaults(fields: NormalizedField[]): JsonObject {
  const defaults: JsonObject = {};
  fields.forEach((field) => {
    if (field.defaultValue !== undefined && field.kind !== 'unsupported') {
      defaults[field.key] = field.defaultValue;
    }
  });
  return defaults;
}

function isMissingRequiredValue(value: unknown): boolean {
  if (value === undefined || value === null) return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  return false;
}

function validateConfig(fields: NormalizedField[], config: JsonObject): Record<string, string> {
  const errors: Record<string, string> = {};
  fields.forEach((field) => {
    if (field.required && field.kind === 'unsupported') {
      errors[field.key] = `Unsupported required config field schema for "${field.key}".`;
      return;
    }
    if (!field.required) return;
    if (isMissingRequiredValue(config[field.key])) {
      errors[field.key] = 'Required.';
    }
  });
  return errors;
}

function pruneConfig(config: JsonObject): JsonObject | null {
  const entries = Object.entries(config).filter(([, value]) => value !== undefined);
  if (entries.length === 0) return null;
  return Object.fromEntries(entries);
}

export default function ConfigForm({ onSubmit, defaultConfig }: ConfigFormProps) {
  const [numAgents, setNumAgents] = useState(defaultConfig.numAgents);
  const [numTurns, setNumTurns] = useState(defaultConfig.numTurns);
  const [feedAlgorithm, setFeedAlgorithm] = useState<string>(defaultConfig.feedAlgorithm);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [showAlgorithmSettings, setShowAlgorithmSettings] = useState(false);
  const [feedAlgorithmConfigByAlgId, setFeedAlgorithmConfigByAlgId] = useState<
    Record<string, JsonObject>
  >(() => (defaultConfig.feedAlgorithmConfig ? { [defaultConfig.feedAlgorithm]: defaultConfig.feedAlgorithmConfig } : {}));
  const [feedAlgorithmConfig, setFeedAlgorithmConfig] = useState<JsonObject>(
    defaultConfig.feedAlgorithmConfig || {},
  );
  const [algorithms, setAlgorithms] = useState<FeedAlgorithm[]>([]);
  const algorithmsRequestIdRef = useRef<number>(0);

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

            {schemaFields.length > 0 && (
              <div className="mt-3">
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    aria-expanded={showAlgorithmSettings}
                    onClick={() => setShowAlgorithmSettings((v) => !v)}
                    className="text-sm font-medium text-beige-800 hover:text-beige-900 transition-colors"
                  >
                    {showAlgorithmSettings ? '▾' : '▸'} Algorithm settings
                  </button>
                  {Object.keys(configErrors).length > 0 && (
                    <span className="text-xs text-red-600">Fix required fields</span>
                  )}
                </div>

                {showAlgorithmSettings && (
                  <div className="mt-3 ml-3 pl-4 border-l border-beige-200">
                    <div className="space-y-4">
                      {schemaFields.map((field) => {
                        const error = submitAttempted ? configErrors[field.key] : null;
                        if (field.kind === 'unsupported') {
                          return (
                            <div key={field.key} className="text-sm text-beige-700">
                              <div className="font-medium">{field.label}</div>
                              {field.description && (
                                <div className="text-beige-600">{field.description}</div>
                              )}
                              <div className="mt-1 text-xs text-red-600">
                                Unsupported config field schema for &quot;{field.key}&quot;.
                              </div>
                              {error && (
                                <div className="mt-1 text-xs text-red-600">{error}</div>
                              )}
                            </div>
                          );
                        }

                        if (field.kind === 'boolean') {
                          const checked = Boolean(feedAlgorithmConfig[field.key]);
                          return (
                            <div key={field.key}>
                              <label className="flex items-center gap-2 text-sm text-beige-800">
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={(e) =>
                                    setConfigValue(field.key, e.currentTarget.checked)
                                  }
                                  className="h-4 w-4 accent-accent"
                                />
                                <span className="font-medium">{field.label}</span>
                              </label>
                              {field.description && (
                                <p className="mt-1 text-sm text-beige-600">
                                  {field.description}
                                </p>
                              )}
                              {error && (
                                <p className="mt-1 text-xs text-red-600">{error}</p>
                              )}
                            </div>
                          );
                        }

                        if (field.kind === 'string_enum') {
                          const value =
                            typeof feedAlgorithmConfig[field.key] === 'string'
                              ? (feedAlgorithmConfig[field.key] as string)
                              : '';
                          return (
                            <div key={field.key}>
                              <label className="block text-sm font-medium text-beige-800 mb-2">
                                {field.label}
                              </label>
                              <select
                                value={value}
                                onChange={(e) =>
                                  setConfigValue(
                                    field.key,
                                    e.target.value ? e.target.value : undefined,
                                  )
                                }
                                className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                              >
                                <option value="">Select…</option>
                                {(field.enumValues || []).map((opt) => (
                                  <option key={opt} value={opt}>
                                    {opt}
                                  </option>
                                ))}
                              </select>
                              {field.description && (
                                <p className="mt-1 text-sm text-beige-600">
                                  {field.description}
                                </p>
                              )}
                              {error && (
                                <p className="mt-1 text-xs text-red-600">{error}</p>
                              )}
                            </div>
                          );
                        }

                        if (field.kind === 'string') {
                          const value =
                            typeof feedAlgorithmConfig[field.key] === 'string'
                              ? (feedAlgorithmConfig[field.key] as string)
                              : '';
                          return (
                            <div key={field.key}>
                              <label className="block text-sm font-medium text-beige-800 mb-2">
                                {field.label}
                              </label>
                              <input
                                type="text"
                                value={value}
                                onChange={(e) =>
                                  setConfigValue(field.key, e.currentTarget.value || undefined)
                                }
                                className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                              />
                              {field.description && (
                                <p className="mt-1 text-sm text-beige-600">
                                  {field.description}
                                </p>
                              )}
                              {error && (
                                <p className="mt-1 text-xs text-red-600">{error}</p>
                              )}
                            </div>
                          );
                        }

                        if (field.kind === 'integer' || field.kind === 'number') {
                          const rawValue = feedAlgorithmConfig[field.key];
                          const value = typeof rawValue === 'number' ? String(rawValue) : '';
                          const step = field.kind === 'integer' ? 1 : 'any';
                          return (
                            <div key={field.key}>
                              <label className="block text-sm font-medium text-beige-800 mb-2">
                                {field.label}
                              </label>
                              <input
                                type="number"
                                value={value}
                                min={field.minimum}
                                max={field.maximum}
                                step={step}
                                onChange={(e) => {
                                  const nextValue = Number(e.currentTarget.value);
                                  if (Number.isNaN(nextValue)) {
                                    setConfigValue(field.key, undefined);
                                    return;
                                  }
                                  setConfigValue(
                                    field.key,
                                    field.kind === 'integer'
                                      ? Math.trunc(nextValue)
                                      : nextValue,
                                  );
                                }}
                                className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                              />
                              {field.description && (
                                <p className="mt-1 text-sm text-beige-600">
                                  {field.description}
                                </p>
                              )}
                              {error && (
                                <p className="mt-1 text-xs text-red-600">{error}</p>
                              )}
                            </div>
                          );
                        }

                        return null;
                      })}
                    </div>

                    {Object.keys(configErrors).length > 0 && (
                      <p className="mt-3 text-xs text-red-600">
                        Fix the highlighted algorithm settings to start the simulation.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
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
