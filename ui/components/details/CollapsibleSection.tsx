'use client';

interface CollapsibleSectionProps {
  title: string;
  count?: number;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

export default function CollapsibleSection({
  title,
  count,
  isOpen,
  onToggle,
  children,
}: CollapsibleSectionProps) {
  const heading: string = count === undefined ? title : `${title} (${count})`;

  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left flex items-center justify-between p-2 hover:bg-beige-100 rounded transition-colors"
      >
        <span className="text-sm font-medium text-beige-800">{heading}</span>
        <span className="text-beige-600">{isOpen ? '▼' : '▶'}</span>
      </button>
      {isOpen && <div className="mt-2">{children}</div>}
    </div>
  );
}
