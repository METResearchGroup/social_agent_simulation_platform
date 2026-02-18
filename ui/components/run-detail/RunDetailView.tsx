'use client';

import DetailsPanel from '@/components/details/DetailsPanel';
import TurnHistorySidebar from '@/components/sidebars/TurnHistorySidebar';

export default function RunDetailView() {
  return (
    <>
      <TurnHistorySidebar />
      <DetailsPanel />
    </>
  );
}
