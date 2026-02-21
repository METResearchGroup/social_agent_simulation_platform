'use client';

import AppTabs from '@/components/layout/AppTabs';

interface SimulationLayoutProps {
  children: React.ReactNode;
}

export default function SimulationLayout({ children }: SimulationLayoutProps) {
  return (
    <div className="flex h-screen w-full flex-col bg-background overflow-hidden">
      <header className="shrink-0 border-b border-beige-300 bg-beige-50">
        <div className="flex items-center justify-between gap-4 px-4 py-2">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-beige-900">
              Agent Simulation Platform
            </div>
            <div className="truncate text-xs text-beige-600">
              Simulation • PDF Upload (dummy)
            </div>
          </div>
          <AppTabs />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
