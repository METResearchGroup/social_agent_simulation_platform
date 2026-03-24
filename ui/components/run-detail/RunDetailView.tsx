'use client';

import DetailsPanel from '@/components/details/DetailsPanel';
import TurnHistorySidebar from '@/components/sidebars/TurnHistorySidebar';
import TurnsErrorBanner from '@/components/run-detail/TurnsErrorBanner';

export default function RunDetailView() {
  return (
    <div className="flex-1 flex flex-col min-w-0">
      <div className="shrink-0 p-2">
        <TurnsErrorBanner />
      </div>
      <div className="flex-1 flex min-w-0 min-h-0">
        <TurnHistorySidebar />
        <div className="flex-1 min-h-0 min-w-0 flex flex-col">
          <DetailsPanel />
        </div>
      </div>
    </div>
  );
}
