'use client';

import { useRunDetail } from '@/components/run-detail/RunDetailContext';

export default function TurnHistorySidebar() {
  const { availableTurns, selectedTurn, onSelectTurn, turnsLoading, turnsError, onRetryTurns } =
    useRunDetail();

  const turnListContent = (): React.ReactNode => {

    /* Case 1: Loading: Show loading indicator */
    if (turnsLoading && availableTurns.length === 0) {
      return (
        <p className="p-4 text-center text-sm text-beige-600">Loading turns…</p>
      );
    }

    /* Case 2: Error: Show error message and retry button when there is an
    error with loading turns. */
    if (turnsError) {
      return (
        <div className="flex flex-col gap-3 p-4 text-beige-800">
          <p className="text-sm">{turnsError.message}</p>
          <button
            type="button"
            onClick={onRetryTurns}
            className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover"
          >
            Retry
          </button>
        </div>
      );
    }

    return availableTurns.map((turnNumber) => (
      <button
        key={turnNumber}
        type="button"
        data-testid={`turn-${turnNumber}`}
        onClick={() => onSelectTurn(turnNumber)}
        className={`w-full text-left p-3 border-b border-beige-200 hover:bg-beige-100 transition-colors ${
          selectedTurn === turnNumber ? 'bg-beige-200' : ''
        }`}
      >
        <div className="text-sm font-medium text-beige-900">
          Turn {turnNumber + 1}
        </div>
      </button>
    ));
  };

  return (
    <div className="w-1/4 border-r border-beige-300 bg-beige-50 flex flex-col">
      <div className="p-4 border-b border-beige-300">
        <h2 className="text-sm font-medium text-beige-900">Run Summary</h2>
      </div>
      <button
        type="button"
        onClick={() => onSelectTurn('summary')}
        className={`w-full text-left p-3 border-b border-beige-200 hover:bg-beige-100 transition-colors ${
          selectedTurn === 'summary' ? 'bg-beige-200' : ''
        }`}
      >
        <div className="text-sm font-medium text-beige-900">Summary</div>
      </button>
      <div className="flex-1 overflow-y-auto">{turnListContent()}</div>
    </div>
  );
}
