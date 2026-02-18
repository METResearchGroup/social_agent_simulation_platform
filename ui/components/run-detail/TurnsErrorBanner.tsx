'use client';

import { useRunDetail } from '@/components/run-detail/RunDetailContext';
import { ApiError } from '@/types';

function getErrorMessage(error: ApiError): string {
  if (error.code === 'RUN_NOT_FOUND') {
    return 'Run not found. It may have been deleted.';
  }
  if (error.code === 'INTERNAL_ERROR' || (error.status >= 500 && error.status < 600)) {
    return 'Server error. Please try again.';
  }
  return error.message || 'Failed to load turns.';
}

export default function TurnsErrorBanner() {
  const { turnsError, retryTurns, selectedRun } = useRunDetail();

  if (!turnsError || !selectedRun) {
    return null;
  }

  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3 bg-beige-100 border border-beige-300 rounded-lg text-beige-800">
      <span className="text-sm">{getErrorMessage(turnsError)}</span>
      <button
        type="button"
        onClick={() => retryTurns(selectedRun.runId)}
        className="shrink-0 px-3 py-1.5 text-sm font-medium rounded-md bg-accent hover:bg-accent-hover text-beige-900 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}
