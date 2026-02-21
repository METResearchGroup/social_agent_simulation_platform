'use client';

import { useId, useState } from 'react';

function isProbablyPdf(file: File): boolean {
  if (file.type === 'application/pdf') return true;
  return file.name.toLowerCase().endsWith('.pdf');
}

export default function PdfUploadCard() {
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const onSelectFile = (nextFile: File | null): void => {
    setError(null);
    setFile(null);

    if (!nextFile) return;
    if (!isProbablyPdf(nextFile)) {
      setError('Please select a PDF file.');
      return;
    }
    setFile(nextFile);
  };

  return (
    <section className="w-full max-w-xl rounded-xl border border-beige-300 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-beige-900">PDF upload (dummy)</h1>
        <p className="mt-1 text-sm text-beige-700">
          Frontend-only for now. When you select a PDF, we’ll display its filename.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <label
          htmlFor={inputId}
          onDragEnter={() => setIsDragging(true)}
          onDragLeave={() => setIsDragging(false)}
          onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(false);
            onSelectFile(e.dataTransfer.files?.[0] ?? null);
          }}
          className={[
            'flex cursor-pointer items-center justify-center rounded-lg border border-dashed px-4 py-8 text-center text-sm transition-colors',
            isDragging
              ? 'border-accent bg-beige-100 text-beige-900'
              : 'border-beige-300 bg-beige-50 text-beige-700 hover:bg-beige-100',
          ].join(' ')}
        >
          <span className="font-medium text-beige-900">Click to choose</span>
          <span className="mx-1 text-beige-600">or</span>
          <span className="text-beige-700">drag-and-drop a PDF</span>
        </label>

        <input
          id={inputId}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => onSelectFile(e.target.files?.[0] ?? null)}
        />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </div>
        )}

        <div className="rounded-lg border border-beige-200 bg-beige-50 px-3 py-2">
          <div className="text-xs font-medium text-beige-700">Selected file</div>
          <div className="mt-0.5 text-sm text-beige-900">
            {file ? file.name : <span className="text-beige-600">None</span>}
          </div>
        </div>

        {file && (
          <button
            type="button"
            className="self-start rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
            onClick={() => onSelectFile(null)}
          >
            Clear selection
          </button>
        )}
      </div>
    </section>
  );
}

