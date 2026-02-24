'use client';

import type { JsonObject, NormalizedField } from '@/components/form/config-schema';

interface AlgorithmSettingsSectionProps {
  schemaFields: NormalizedField[];
  feedAlgorithmConfig: JsonObject;
  configErrors: Record<string, string>;
  submitAttempted: boolean;
  showAlgorithmSettings: boolean;
  onToggleShowAlgorithmSettings: () => void;
  onSetConfigValue: (key: string, value: unknown | undefined) => void;
}

export default function AlgorithmSettingsSection({
  schemaFields,
  feedAlgorithmConfig,
  configErrors,
  submitAttempted,
  showAlgorithmSettings,
  onToggleShowAlgorithmSettings,
  onSetConfigValue,
}: AlgorithmSettingsSectionProps) {
  if (schemaFields.length === 0) {
    return null;
  }

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          aria-expanded={showAlgorithmSettings}
          onClick={onToggleShowAlgorithmSettings}
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
                    {error && <div className="mt-1 text-xs text-red-600">{error}</div>}
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
                        onChange={(e) => onSetConfigValue(field.key, e.currentTarget.checked)}
                        className="h-4 w-4 accent-accent"
                      />
                      <span className="font-medium">{field.label}</span>
                    </label>
                    {field.description && (
                      <p className="mt-1 text-sm text-beige-600">{field.description}</p>
                    )}
                    {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
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
                        onSetConfigValue(field.key, e.target.value ? e.target.value : undefined)
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
                      <p className="mt-1 text-sm text-beige-600">{field.description}</p>
                    )}
                    {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
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
                      onChange={(e) => onSetConfigValue(field.key, e.currentTarget.value || undefined)}
                      className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                    />
                    {field.description && (
                      <p className="mt-1 text-sm text-beige-600">{field.description}</p>
                    )}
                    {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
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
                          onSetConfigValue(field.key, undefined);
                          return;
                        }
                        onSetConfigValue(
                          field.key,
                          field.kind === 'integer' ? Math.trunc(nextValue) : nextValue,
                        );
                      }}
                      className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                    />
                    {field.description && (
                      <p className="mt-1 text-sm text-beige-600">{field.description}</p>
                    )}
                    {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
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
  );
}

