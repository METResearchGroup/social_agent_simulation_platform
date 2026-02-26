'use client';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  ariaLabel: string;
  maxLength?: number;
}

export default function SearchInput({
  value,
  onChange,
  placeholder,
  ariaLabel,
  maxLength = 200,
}: SearchInputProps) {
  const showClear: boolean = value.trim().length > 0;

  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        maxLength={maxLength}
        className="w-full px-3 py-2 pr-10 border border-beige-300 rounded-lg bg-white text-beige-900 text-sm focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
      />
      {showClear ? (
        <button
          type="button"
          onClick={() => onChange('')}
          className="absolute inset-y-0 right-0 px-3 text-beige-600 hover:text-beige-900"
          aria-label="Clear search"
        >
          ×
        </button>
      ) : null}
    </div>
  );
}
