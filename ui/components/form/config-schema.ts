export type JsonObject = Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

export type NormalizedFieldKind =
  | 'string'
  | 'string_enum'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'unsupported';

export interface NormalizedField {
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
      const nonNullSchema = anyOf.find((item) => isRecord(item) && item.type === nonNull) as
        | unknown
        | undefined;
      return nonNullSchema ?? schema;
    }
  }

  return schema;
}

export function normalizeConfigSchema(schema: unknown): NormalizedConfigSchema | null {
  if (!isRecord(schema)) return null;
  if (schema.type !== 'object') return null;

  const properties = schema.properties;
  if (!isRecord(properties)) return null;

  const requiredKeys = isStringArray(schema.required)
    ? new Set(schema.required)
    : new Set<string>();

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

export function buildDefaults(fields: NormalizedField[]): JsonObject {
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

export function validateConfig(
  fields: NormalizedField[],
  config: JsonObject,
): Record<string, string> {
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

export function pruneConfig(config: JsonObject): JsonObject | null {
  const entries = Object.entries(config).filter(([, value]) => value !== undefined);
  if (entries.length === 0) return null;
  return Object.fromEntries(entries);
}

