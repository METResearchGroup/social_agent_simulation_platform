'use client';

import { useRef, useState } from 'react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import CollapsibleSection from '@/components/details/CollapsibleSection';
import { Agent } from '@/types';

interface CreateAgentViewProps {
  agents: Agent[];
  agentsLoading: boolean;
  agentsError: Error | null;
  onRetryAgents?: () => void;
  onSubmit: (payload: {
    handle: string;
    displayName: string;
    bio: string;
  }) => Promise<void>;
}

interface CommentEntry {
  id: string;
  text: string;
  postUri: string;
}

function createCommentEntry(): CommentEntry {
  return {
    id: crypto.randomUUID(),
    text: '',
    postUri: '',
  };
}

export default function CreateAgentView({
  agents,
  agentsLoading,
  agentsError,
  onRetryAgents,
  onSubmit,
}: CreateAgentViewProps) {
  const [handle, setHandle] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [comments, setComments] = useState<CommentEntry[]>(() => [createCommentEntry()]);
  const [likedPostUris, setLikedPostUris] = useState('');
  const [linkedAgentHandles, setLinkedAgentHandles] = useState<string[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<Error | null>(null);
  const isSubmittingRef = useRef(false);

  const handleAddComment = (): void => {
    setComments((prev) => [...prev, createCommentEntry()]);
  };

  const handleRemoveComment = (id: string): void => {
    setComments((prev) => prev.filter((c) => c.id !== id));
  };

  const handleCommentChange = (id: string, field: keyof Omit<CommentEntry, 'id'>, value: string): void => {
    setComments((prev) =>
      prev.map((c) => (c.id === id ? { ...c, [field]: value } : c)),
    );
  };

  const handleLinkedAgentToggle = (agentHandle: string): void => {
    setLinkedAgentHandles((prev) =>
      prev.includes(agentHandle)
        ? prev.filter((h) => h !== agentHandle)
        : [...prev, agentHandle],
    );
  };

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setSubmitError(null);
    setSubmitLoading(true);
    void onSubmit({ handle: handle.trim(), displayName: displayName.trim(), bio: bio.trim() })
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

          <CollapsibleSection
            title="History"
            count={comments.length + likedPostUris.split('\n').filter(Boolean).length}
            isOpen={historyOpen}
            onToggle={() => setHistoryOpen(!historyOpen)}
          >
            <div className="space-y-4 p-3 bg-beige-50 rounded-lg">
              <div>
                <span className="text-sm font-medium text-beige-800">Comments</span>
                <div className="space-y-2 mt-2">
                  {comments.map((comment) => (
                    <div key={comment.id} className="flex gap-2 items-start">
                      <input
                        type="text"
                        value={comment.text}
                        onChange={(e) => handleCommentChange(comment.id, 'text', e.target.value)}
                        className={`${inputClasses} flex-1`}
                        placeholder="Comment text"
                      />
                      <input
                        type="text"
                        value={comment.postUri}
                        onChange={(e) => handleCommentChange(comment.id, 'postUri', e.target.value)}
                        className={`${inputClasses} flex-1`}
                        placeholder="Post URI (optional)"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveComment(comment.id)}
                        className="px-3 py-2 text-sm text-beige-600 hover:text-beige-900"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={handleAddComment}
                    className="text-sm font-medium text-accent hover:text-accent-hover"
                  >
                    + Add comment
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="likedPostUris" className="text-sm font-medium text-beige-800">
                  Liked post URIs (one per line)
                </label>
                <textarea
                  id="likedPostUris"
                  value={likedPostUris}
                  onChange={(e) => setLikedPostUris(e.target.value)}
                  className={`${inputClasses} min-h-[60px] mt-1`}
                  placeholder="at://did:plc:.../app.bsky.feed.post/..."
                  rows={3}
                />
              </div>
            </div>
          </CollapsibleSection>

          <CollapsibleSection
            title="Link to existing agents"
            count={linkedAgentHandles.length}
            isOpen={linkOpen}
            onToggle={() => setLinkOpen(!linkOpen)}
          >
            <div className="p-3 bg-beige-50 rounded-lg space-y-2">
              {agentsLoading && agents.length === 0 ? (
                <div className="flex items-center gap-2 text-beige-600">
                  <LoadingSpinner />
                  <span className="text-sm">Loading agents…</span>
                </div>
              ) : agentsError ? (
                <div className="flex flex-col gap-3 text-beige-800">
                  <p className="text-sm">{agentsError.message}</p>
                  {onRetryAgents != null && (
                    <button
                      type="button"
                      onClick={onRetryAgents}
                      className="px-3 py-2 text-sm font-medium text-accent hover:text-accent-hover w-fit"
                    >
                      Retry
                    </button>
                  )}
                </div>
              ) : agents.length === 0 ? (
                <p className="text-sm text-beige-600">No agents available</p>
              ) : (
                agents.map((agent) => (
                  <label
                    key={agent.handle}
                    className="flex items-center gap-2 cursor-pointer hover:bg-beige-100 p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={linkedAgentHandles.includes(agent.handle)}
                      onChange={() => handleLinkedAgentToggle(agent.handle)}
                      className="rounded border-beige-300"
                    />
                    <span className="text-sm text-beige-900">
                      {agent.name} <span className="text-beige-600">({agent.handle})</span>
                    </span>
                  </label>
                ))
              )}
            </div>
          </CollapsibleSection>

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
