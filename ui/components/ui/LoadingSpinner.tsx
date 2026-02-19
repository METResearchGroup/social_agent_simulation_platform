'use client';

export default function LoadingSpinner() {
  return (
    <div
      className="h-5 w-5 animate-spin rounded-full border-2 border-beige-300 border-t-accent"
      aria-hidden
    />
  );
}
