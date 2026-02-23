'use client';

import LoadingSpinner from '@/components/ui/LoadingSpinner';
import StartView from '@/components/start/StartView';
import { FALLBACK_DEFAULT_CONFIG } from '@/lib/default-config';
import type { RunConfig } from '@/types';

interface StartScreenViewProps {
  defaultConfig: RunConfig | null;
  defaultConfigLoading: boolean;
  defaultConfigError: Error | null;
  onRetryConfig: () => void;
  onSubmit: (config: RunConfig) => void;
}

export default function StartScreenView({
  defaultConfig,
  defaultConfigLoading,
  defaultConfigError,
  onRetryConfig,
  onSubmit,
}: StartScreenViewProps) {
  if (defaultConfigLoading && defaultConfig === null) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-beige-600">
        <LoadingSpinner />
        <span className="text-sm">Loading form…</span>
      </div>
    );
  }

  if (defaultConfigError) {
    return (
      <div className="flex flex-col gap-3 p-8 text-beige-800">
        <p className="text-sm">{defaultConfigError.message}</p>
        <button
          type="button"
          onClick={onRetryConfig}
          className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
        >
          Retry
        </button>
        <StartView
          onSubmit={onSubmit}
          defaultConfig={defaultConfig ?? FALLBACK_DEFAULT_CONFIG}
        />
      </div>
    );
  }

  return (
    <StartView
      onSubmit={onSubmit}
      defaultConfig={defaultConfig ?? FALLBACK_DEFAULT_CONFIG}
    />
  );
}
