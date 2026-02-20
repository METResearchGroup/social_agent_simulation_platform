import { ApiError } from '@/types';

/**
 * Returns a user-friendly message for turns fetch errors.
 * Avoids leaking technical details; uses code for RUN_NOT_FOUND and 5xx.
 */
export function getTurnsErrorMessage(error: ApiError): string {
  if (error.code === 'RUN_NOT_FOUND') {
    return 'Run not found. It may have been deleted.';
  }
  if (error.code === 'INTERNAL_ERROR' || (error.status >= 500 && error.status < 600)) {
    return 'Server error. Please try again.';
  }
  return error.message || 'Failed to load turns.';
}
