'use client';

import { useRunDetail } from '@/components/run-detail/RunDetailContext';
import { getTurnsErrorMessage } from '@/lib/error-messages';

export default function TurnsErrorBanner() {
  const { turnsError, onRetryTurns, selectedRun } = useRunDetail();

  if (!turnsError || !selectedRun) {
    return null;
  }

  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3 bg-beige-100 border border-beige-300 rounded-lg text-beige-800">
      <span className="text-sm">{getTurnsErrorMessage(turnsError)}</span>
      <button
        type="button"
        onClick={onRetryTurns}
        className="shrink-0 px-3 py-1.5 text-sm font-medium rounded-md bg-accent hover:bg-accent-hover text-beige-900 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}
