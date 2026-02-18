'use client';

interface SimulationLayoutProps {
  children: React.ReactNode;
}

export default function SimulationLayout({ children }: SimulationLayoutProps) {
  return <div className="flex h-screen w-full bg-background overflow-hidden">{children}</div>;
}
