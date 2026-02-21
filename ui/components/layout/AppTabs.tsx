'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

function tabClassName(isActive: boolean): string {
  return [
    'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
    isActive
      ? 'bg-accent text-beige-900'
      : 'text-beige-700 hover:text-beige-900 hover:bg-beige-100',
  ].join(' ');
}

export default function AppTabs() {
  const pathname = usePathname();
  const isSimulationActive = pathname === '/';
  const isPdfActive = pathname === '/pdf-upload';

  return (
    <nav aria-label="App tabs" className="shrink-0">
      <div className="inline-flex items-center gap-1 rounded-lg border border-beige-300 bg-white p-1">
        <Link href="/" className={tabClassName(isSimulationActive)}>
          Simulation
        </Link>
        <Link href="/pdf-upload" className={tabClassName(isPdfActive)}>
          PDF Upload
        </Link>
      </div>
    </nav>
  );
}

