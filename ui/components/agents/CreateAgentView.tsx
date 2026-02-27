'use client';

import { useRef, useState } from 'react';

interface CreateAgentViewProps {
  onSubmit: (payload: {
    handle: string;
    displayName: string;
    bio: string;
  }) => Promise<void>;
}

export default function CreateAgentView({ onSubmit }: CreateAgentViewProps) {
  const [handle, setHandle] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<Error | null>(null);
  const isSubmittingRef = useRef(false);

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setSubmitError(null);
    setSubmitLoading(true);
    void Promise.resolve()
      .then(() =>
        onSubmit({
          handle: handle.trim(),
          displayName: displayName.trim(),
          bio: bio.trim(),
        }),
      )
      .catch((err: unknown) => {
        setSubmitError(err instanceof Error ? err : new Error(String(err)));
      })
      .finally(() => {
        setSubmitLoading(false);
        isSubmittingRef.current = false;
      });
  };

  const inputClasses =
    'w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent';
  const labelClasses = 'block text-sm font-medium text-beige-800 mb-2';

  return (
    <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
      <div className="w-full max-w-lg">
        <h1 className="text-2xl font-semibold text-beige-900 mb-8 text-center">
          Create New Agent
        </h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="handle" className={labelClasses}>
              Handle <span className="text-beige-500">(required)</span>
            </label>
            <input
              id="handle"
              type="text"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              className={inputClasses}
              placeholder="user.bsky.social"
              required
            />
          </div>
          <div>
            <label htmlFor="displayName" className={labelClasses}>
              Display name <span className="text-beige-500">(required)</span>
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className={inputClasses}
              placeholder="Display Name"
              required
            />
          </div>
          <div>
            <label htmlFor="bio" className={labelClasses}>
              Bio
            </label>
            <textarea
              id="bio"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className={`${inputClasses} min-h-[80px]`}
              placeholder="Agent bio..."
              rows={3}
            />
          </div>

          {submitError != null && (
            <div className="p-3 rounded-lg bg-red-50 text-red-800 text-sm">
              {submitError.message}
            </div>
          )}

          <button
            type="button"
            onClick={() => {}}
            className="w-full px-6 py-3 border border-beige-300 rounded-lg font-medium text-beige-800 hover:bg-beige-100 transition-colors"
          >
            Create AI-generated bio (coming soon)
          </button>

          <button
            type="submit"
            disabled={submitLoading}
            className="w-full px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent-hover transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitLoading ? 'Creating…' : 'Submit'}
          </button>
        </form>
      </div>
    </div>
  );
}
