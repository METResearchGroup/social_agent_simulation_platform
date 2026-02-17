'use client';

import { useRunDetail } from '@/components/run-detail/RunDetailContext';

export default function TurnHistorySidebar() {
  const { availableTurns, selectedTurn, onSelectTurn } = useRunDetail();

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
      <div className="flex-1 overflow-y-auto">
        {availableTurns.map((turnNumber) => (
          <button
            key={turnNumber}
            type="button"
            onClick={() => onSelectTurn(turnNumber)}
            className={`w-full text-left p-3 border-b border-beige-200 hover:bg-beige-100 transition-colors ${
              selectedTurn === turnNumber ? 'bg-beige-200' : ''
            }`}
          >
            <div className="text-sm font-medium text-beige-900">
              Turn {turnNumber + 1}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
