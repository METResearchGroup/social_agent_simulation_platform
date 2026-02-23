'use client';

import { useEffect, useRef, useState } from 'react';
import { getFeedAlgorithms } from '@/lib/api/simulation';
import { FeedAlgorithm, RunConfig } from '@/types';

interface ConfigFormProps {
  onSubmit: (config: RunConfig) => void;
  defaultConfig: RunConfig;
}

type AlgorithmConfigPrimitiveType = 'string' | 'number' | 'integer' | 'boolean';

interface AlgorithmConfigFieldSchema {
  type?: AlgorithmConfigPrimitiveType;
  enum?: Array<string | number>;
  default?: unknown;
  title?: string;
  description?: string;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
}

interface AlgorithmConfigSchema {
  type: 'object';
  properties: Record<string, AlgorithmConfigFieldSchema>;
  required?: string[];
}

interface ParsedAlgorithmConfigSchema {
  schema: AlgorithmConfigSchema | null;
  unsupportedReason: string | null;
  unsupportedFields: string[];
}

interface RenderableAlgorithmConfigField {
  name: string;
  schema: AlgorithmConfigFieldSchema & { type: AlgorithmConfigPrimitiveType };
  isRequired: boolean;
}

const DEBUG_FALLBACK_SCHEMA: AlgorithmConfigSchema = {
  type: 'object',
  properties: {
    max_posts: {
      type: 'integer',
      title: 'Max Posts',
      description: 'Maximum number of posts to include in each feed.',
      default: 20,
      minimum: 1,
      maximum: 100,
    },
    tie_breaker: {
      type: 'string',
      title: 'Tie Breaker',
      description: 'Secondary sort key when primary scores tie.',
      enum: ['uri', 'created_at'],
      default: 'uri',
    },
    include_replies: {
      type: 'boolean',
      title: 'Include Replies',
      description: 'Whether to allow reply posts in the feed.',
      default: false,
    },
  },
  required: ['max_posts'],
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseAlgorithmConfigSchema(
  raw: Record<string, unknown> | null,
): ParsedAlgorithmConfigSchema {
  if (raw === null) {
    return { schema: null, unsupportedReason: null, unsupportedFields: [] };
  }

  if (!isRecord(raw)) {
    return {
      schema: null,
      unsupportedReason: 'This algorithm has settings the UI can’t render yet.',
      unsupportedFields: [],
    };
  }

  if (raw.type !== 'object' || !isRecord(raw.properties)) {
    return {
      schema: null,
      unsupportedReason: 'This algorithm has settings the UI can’t render yet.',
      unsupportedFields: [],
    };
  }

  const properties: Record<string, AlgorithmConfigFieldSchema> = {};
  const unsupportedFields: string[] = [];

  Object.entries(raw.properties).forEach(([key, v]) => {
    if (!isRecord(v)) {
      unsupportedFields.push(key);
      return;
    }

    const typeRaw: unknown = v.type;
    const type: AlgorithmConfigPrimitiveType =
      typeRaw === 'string' || typeRaw === 'number' || typeRaw === 'integer' || typeRaw === 'boolean'
        ? typeRaw
        : 'string';

    const title: string | undefined = typeof v.title === 'string' ? v.title : undefined;
    const description: string | undefined =
      typeof v.description === 'string' ? v.description : undefined;

    const enumRaw: unknown = v.enum;
    const enumValues: Array<string | number> | undefined = Array.isArray(enumRaw)
      ? (enumRaw.filter(
          (item): item is string | number => typeof item === 'string' || typeof item === 'number',
        ) as Array<string | number>)
      : undefined;
    const hasInvalidEnum: boolean =
      Array.isArray(enumRaw) && enumValues !== undefined && enumValues.length !== enumRaw.length;

    if (
      Array.isArray(enumRaw) &&
      (enumValues === undefined || enumValues.length === 0 || hasInvalidEnum)
    ) {
      unsupportedFields.push(key);
      return;
    }

    const minimum: number | undefined = typeof v.minimum === 'number' ? v.minimum : undefined;
    const maximum: number | undefined = typeof v.maximum === 'number' ? v.maximum : undefined;
    const minLength: number | undefined = typeof v.minLength === 'number' ? v.minLength : undefined;
    const maxLength: number | undefined = typeof v.maxLength === 'number' ? v.maxLength : undefined;

    properties[key] = {
      type,
      enum: enumValues,
      default: 'default' in v ? v.default : undefined,
      title,
      description,
      minimum,
      maximum,
      minLength,
      maxLength,
    };
  });

  const requiredRaw: unknown = raw.required;
  const required: string[] | undefined = Array.isArray(requiredRaw)
    ? requiredRaw.filter((item): item is string => typeof item === 'string')
    : undefined;

  return {
    schema: { type: 'object', properties, required },
    unsupportedReason:
      unsupportedFields.length > 0 ? 'Some algorithm settings can’t be rendered yet.' : null,
    unsupportedFields,
  };
}

function getRenderableFields(schema: AlgorithmConfigSchema): RenderableAlgorithmConfigField[] {
  const required: ReadonlySet<string> = new Set(schema.required ?? []);
  return Object.keys(schema.properties)
    .sort((a, b) => a.localeCompare(b))
    .map((name) => {
      const field = schema.properties[name];
      const type: AlgorithmConfigPrimitiveType = field.type ?? 'string';
      return {
        name,
        schema: { ...field, type },
        isRequired: required.has(name),
      };
    });
}

function coerceDefaultValue(
  field: RenderableAlgorithmConfigField,
  rawDefault: unknown,
): string | number | boolean | null {
  if (rawDefault === null || rawDefault === undefined) {
    return null;
  }

  if (field.schema.enum && field.schema.enum.length > 0) {
    const matchesEnum: boolean = field.schema.enum.some((v) => v === rawDefault);
    return matchesEnum ? (rawDefault as string | number) : null;
  }

  switch (field.schema.type) {
    case 'boolean':
      return typeof rawDefault === 'boolean' ? rawDefault : null;
    case 'integer':
      return typeof rawDefault === 'number' && Number.isFinite(rawDefault)
        ? Math.trunc(rawDefault)
        : null;
    case 'number':
      return typeof rawDefault === 'number' && Number.isFinite(rawDefault) ? rawDefault : null;
    case 'string':
    default:
      return typeof rawDefault === 'string' ? rawDefault : null;
  }
}

function applyAlgorithmSchemaDefaults(
  existingConfig: Record<string, unknown>,
  effectiveSchema: Record<string, unknown> | null,
): { nextConfig: Record<string, unknown>; changed: boolean } {
  const parsed: ParsedAlgorithmConfigSchema = parseAlgorithmConfigSchema(effectiveSchema);
  if (!parsed.schema) {
    return { nextConfig: existingConfig, changed: false };
  }

  const fields: RenderableAlgorithmConfigField[] = getRenderableFields(parsed.schema);
  const nextConfig: Record<string, unknown> = { ...existingConfig };
  let changed: boolean = false;

  fields.forEach((field) => {
    if (nextConfig[field.name] !== undefined) {
      return;
    }

    const coercedDefault = coerceDefaultValue(field, field.schema.default);
    if (coercedDefault !== null) {
      nextConfig[field.name] = coercedDefault;
      changed = true;
      return;
    }

    if (field.isRequired && field.schema.type === 'boolean') {
      nextConfig[field.name] = false;
      changed = true;
    }
  });

  return { nextConfig, changed };
}

export default function ConfigForm({ onSubmit, defaultConfig }: ConfigFormProps) {
  const [numAgents, setNumAgents] = useState(defaultConfig.numAgents);
  const [numTurns, setNumTurns] = useState(defaultConfig.numTurns);
  const [feedAlgorithm, setFeedAlgorithm] = useState<string>(defaultConfig.feedAlgorithm);
  const [feedAlgorithmConfigById, setFeedAlgorithmConfigById] = useState<
    Record<string, Record<string, unknown>>
  >({
    [defaultConfig.feedAlgorithm]: defaultConfig.feedAlgorithmConfig,
  });
  const [algorithmFieldErrors, setAlgorithmFieldErrors] = useState<Record<string, string>>({});
  const [algorithms, setAlgorithms] = useState<FeedAlgorithm[]>([]);
  const algorithmsRequestIdRef = useRef<number>(0);
  const initialFeedAlgorithmIdRef = useRef<string>(defaultConfig.feedAlgorithm);

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
        const initialFeedAlgorithmId: string = initialFeedAlgorithmIdRef.current;
        const debugEnabled: boolean = process.env.NEXT_PUBLIC_DEBUG_ALGO_SCHEMA === 'true';
        const initialAlg: FeedAlgorithm | undefined = list.find(
          (a) => a.id === initialFeedAlgorithmId,
        );
        const initialSchema: Record<string, unknown> | null =
          initialAlg?.configSchema ??
          (debugEnabled
            ? (DEBUG_FALLBACK_SCHEMA as unknown as Record<string, unknown>)
            : null);

        setFeedAlgorithmConfigById((prev) => {
          const existingConfig: Record<string, unknown> = prev[initialFeedAlgorithmId] ?? {};
          if (initialSchema === null) {
            if (prev[initialFeedAlgorithmId]) {
              return prev;
            }
            return { ...prev, [initialFeedAlgorithmId]: {} };
          }

          const { nextConfig, changed } = applyAlgorithmSchemaDefaults(
            existingConfig,
            initialSchema,
          );

          if (!changed && prev[initialFeedAlgorithmId]) {
            return prev;
          }
          return { ...prev, [initialFeedAlgorithmId]: nextConfig };
        });
      } catch (err) {
        console.error('Failed to fetch feed algorithms:', err);
      }
    };

    void load();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();

    const currentAlgConfig: Record<string, unknown> = feedAlgorithmConfigById[feedAlgorithm] ?? {};
    const nextErrors: Record<string, string> = {};

    if (renderableAlgorithmFields.length > 0) {
      renderableAlgorithmFields.forEach((field) => {
        const value: unknown = currentAlgConfig[field.name];
        if (field.isRequired && value === undefined) {
          nextErrors[field.name] = 'Required';
          return;
        }

        if (value === undefined) {
          return;
        }

        if (field.schema.enum && field.schema.enum.length > 0) {
          const matchesEnum: boolean = field.schema.enum.some((v) => v === value);
          if (!matchesEnum) {
            nextErrors[field.name] = 'Invalid value';
          }
          return;
        }

        switch (field.schema.type) {
          case 'boolean': {
            if (typeof value !== 'boolean') {
              nextErrors[field.name] = 'Invalid value';
            }
            break;
          }
          case 'integer': {
            if (typeof value !== 'number' || !Number.isFinite(value) || !Number.isInteger(value)) {
              nextErrors[field.name] = 'Invalid value';
              break;
            }
            if (typeof field.schema.minimum === 'number' && value < field.schema.minimum) {
              nextErrors[field.name] = `Must be ≥ ${field.schema.minimum}`;
            }
            if (typeof field.schema.maximum === 'number' && value > field.schema.maximum) {
              nextErrors[field.name] = `Must be ≤ ${field.schema.maximum}`;
            }
            break;
          }
          case 'number': {
            if (typeof value !== 'number' || !Number.isFinite(value)) {
              nextErrors[field.name] = 'Invalid value';
              break;
            }
            if (typeof field.schema.minimum === 'number' && value < field.schema.minimum) {
              nextErrors[field.name] = `Must be ≥ ${field.schema.minimum}`;
            }
            if (typeof field.schema.maximum === 'number' && value > field.schema.maximum) {
              nextErrors[field.name] = `Must be ≤ ${field.schema.maximum}`;
            }
            break;
          }
          case 'string':
          default: {
            if (typeof value !== 'string' || value.trim().length === 0) {
              if (field.isRequired) {
                nextErrors[field.name] = 'Required';
              } else {
                nextErrors[field.name] = 'Invalid value';
              }
              break;
            }
            if (typeof field.schema.minLength === 'number' && value.length < field.schema.minLength) {
              nextErrors[field.name] = `Must be at least ${field.schema.minLength} characters`;
            }
            if (typeof field.schema.maxLength === 'number' && value.length > field.schema.maxLength) {
              nextErrors[field.name] = `Must be at most ${field.schema.maxLength} characters`;
            }
            break;
          }
        }
      });
    }

    if (Object.keys(nextErrors).length > 0) {
      setAlgorithmFieldErrors(nextErrors);
      return;
    }

    setAlgorithmFieldErrors({});
    onSubmit({
      numAgents,
      numTurns,
      feedAlgorithm,
      feedAlgorithmConfig: currentAlgConfig,
    });
  };

  const selectedAlg = algorithms.find((a) => a.id === feedAlgorithm);
  const debugSchemaEnabled: boolean = process.env.NEXT_PUBLIC_DEBUG_ALGO_SCHEMA === 'true';
  const effectiveConfigSchema: Record<string, unknown> | null =
    selectedAlg?.configSchema ??
    (debugSchemaEnabled
      ? (DEBUG_FALLBACK_SCHEMA as unknown as Record<string, unknown>)
      : null);

  const parsedConfigSchema: ParsedAlgorithmConfigSchema =
    parseAlgorithmConfigSchema(effectiveConfigSchema);

  const renderableAlgorithmFields: RenderableAlgorithmConfigField[] = parsedConfigSchema.schema
    ? getRenderableFields(parsedConfigSchema.schema)
    : [];

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
              onChange={(e) => {
                const nextAlgorithmId: string = e.target.value;
                setFeedAlgorithm(nextAlgorithmId);
                setAlgorithmFieldErrors({});
                const nextAlg: FeedAlgorithm | undefined = algorithms.find(
                  (a) => a.id === nextAlgorithmId,
                );
                const nextSchema: Record<string, unknown> | null =
                  nextAlg?.configSchema ??
                  (debugSchemaEnabled
                    ? (DEBUG_FALLBACK_SCHEMA as unknown as Record<string, unknown>)
                    : null);

                setFeedAlgorithmConfigById((prev) => {
                  const existingConfig: Record<string, unknown> = prev[nextAlgorithmId] ?? {};
                  if (nextSchema === null) {
                    if (prev[nextAlgorithmId]) {
                      return prev;
                    }
                    return { ...prev, [nextAlgorithmId]: {} };
                  }

                  const { nextConfig, changed } = applyAlgorithmSchemaDefaults(
                    existingConfig,
                    nextSchema,
                  );
                  if (!changed && prev[nextAlgorithmId]) {
                    return prev;
                  }
                  return { ...prev, [nextAlgorithmId]: nextConfig };
                });
              }}
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
          </div>
          {parsedConfigSchema.schema && renderableAlgorithmFields.length > 0 ? (
            <div>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-beige-800">Algorithm Settings</h2>
                {parsedConfigSchema.unsupportedReason && (
                  <span className="text-xs text-beige-500">{parsedConfigSchema.unsupportedReason}</span>
                )}
              </div>
              <div className="mt-3 space-y-4">
                {renderableAlgorithmFields.map((field) => {
                  const currentAlgConfig: Record<string, unknown> =
                    feedAlgorithmConfigById[feedAlgorithm] ?? {};
                  const value: unknown = currentAlgConfig[field.name];
                  const label: string = field.schema.title ?? field.name;
                  const error: string | undefined = algorithmFieldErrors[field.name];

                  const setFieldValue = (next: unknown | undefined): void => {
                    setFeedAlgorithmConfigById((prev) => {
                      const previousForAlg: Record<string, unknown> = prev[feedAlgorithm] ?? {};
                      const nextForAlg: Record<string, unknown> = { ...previousForAlg };
                      if (next === undefined) {
                        delete nextForAlg[field.name];
                      } else {
                        nextForAlg[field.name] = next;
                      }
                      return { ...prev, [feedAlgorithm]: nextForAlg };
                    });
                    setAlgorithmFieldErrors((prev) => {
                      if (!prev[field.name]) {
                        return prev;
                      }
                      const nextErrors: Record<string, string> = { ...prev };
                      delete nextErrors[field.name];
                      return nextErrors;
                    });
                  };

                  const commonInputClassName: string =
                    'w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent';

                  return (
                    <div key={field.name}>
                      <label className="block text-sm font-medium text-beige-800 mb-2">
                        {label}
                        {field.isRequired ? (
                          <span className="ml-1 text-xs text-beige-500">(required)</span>
                        ) : null}
                      </label>
                      {field.schema.description ? (
                        <p className="mt-0.5 mb-2 text-sm text-beige-600">{field.schema.description}</p>
                      ) : null}

                      {field.schema.enum && field.schema.enum.length > 0 ? (
                        <select
                          value={value === undefined ? '' : String(value)}
                          onChange={(e) => {
                            const raw: string = e.target.value;
                            if (raw === '') {
                              setFieldValue(undefined);
                              return;
                            }
                            const enumValues = field.schema.enum ?? [];
                            const allNumericEnum: boolean = enumValues.every(
                              (v) => typeof v === 'number',
                            );
                            if (allNumericEnum) {
                              const parsed: number = Number(raw);
                              if (Number.isFinite(parsed) && enumValues.some((v) => v === parsed)) {
                                setFieldValue(parsed);
                              } else {
                                setFieldValue(undefined);
                              }
                            } else {
                              setFieldValue(raw);
                            }
                          }}
                          className={commonInputClassName}
                        >
                          <option value="">
                            {field.isRequired ? 'Select…' : 'None'}
                          </option>
                          {field.schema.enum.map((opt) => (
                            <option key={String(opt)} value={String(opt)}>
                              {String(opt)}
                            </option>
                          ))}
                        </select>
                      ) : field.schema.type === 'boolean' ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={typeof value === 'boolean' ? value : false}
                            onChange={(e) => setFieldValue(e.target.checked)}
                            className="h-4 w-4 rounded border-beige-300 text-accent focus:ring-accent"
                          />
                          <span className="text-sm text-beige-700">Enabled</span>
                        </div>
                      ) : field.schema.type === 'integer' || field.schema.type === 'number' ? (
                        <input
                          type="number"
                          step={field.schema.type === 'integer' ? 1 : 'any'}
                          min={typeof field.schema.minimum === 'number' ? field.schema.minimum : undefined}
                          max={typeof field.schema.maximum === 'number' ? field.schema.maximum : undefined}
                          value={typeof value === 'number' && Number.isFinite(value) ? String(value) : ''}
                          onChange={(e) => {
                            const raw: string = e.currentTarget.value;
                            if (raw.trim() === '') {
                              setFieldValue(undefined);
                              return;
                            }
                            const parsed: number = Number(raw);
                            if (!Number.isFinite(parsed)) {
                              setFieldValue(undefined);
                              return;
                            }
                            setFieldValue(field.schema.type === 'integer' ? Math.trunc(parsed) : parsed);
                          }}
                          className={commonInputClassName}
                        />
                      ) : (
                        <input
                          type="text"
                          minLength={
                            typeof field.schema.minLength === 'number' ? field.schema.minLength : undefined
                          }
                          maxLength={
                            typeof field.schema.maxLength === 'number' ? field.schema.maxLength : undefined
                          }
                          value={typeof value === 'string' ? value : ''}
                          onChange={(e) => {
                            const raw: string = e.currentTarget.value;
                            if (raw === '') {
                              setFieldValue(undefined);
                              return;
                            }
                            setFieldValue(raw);
                          }}
                          className={commonInputClassName}
                        />
                      )}

                      {error ? <p className="mt-1 text-sm text-red-600">{error}</p> : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : parsedConfigSchema.unsupportedReason ? (
            <div className="text-sm text-beige-600">{parsedConfigSchema.unsupportedReason}</div>
          ) : null}
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
            className="w-full px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent-hover transition-colors"
          >
            Start Simulation
          </button>
        </form>
      </div>
    </div>
  );
}
