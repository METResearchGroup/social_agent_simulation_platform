'use client';

import { Dispatch, SetStateAction, useMemo, useState } from 'react';
import { Agent, AgentAction, Post } from '@/types';
import PostCard from '@/components/posts/PostCard';
import CollapsibleSection from '@/components/details/CollapsibleSection';

interface AgentDetailProps {
  agent: Agent;
  feed: Post[];
  actions: AgentAction[];
  allPosts: Post[];
}

interface ExpandedSectionsState {
  metadata: boolean;
  feed: boolean;
  likes: boolean;
  comments: boolean;
}

export default function AgentDetail({
  agent,
  feed,
  actions,
  allPosts,
}: AgentDetailProps) {
  const [expandedSections, setExpandedSections] = useState<ExpandedSectionsState>({
    metadata: false,
    feed: false,
    likes: false,
    comments: false,
  });

  const postsByUri: Record<string, Post> = useMemo(() => {
    const byUri: Record<string, Post> = {};
    for (const post of allPosts) {
      byUri[post.uri] = post;
    }
    return byUri;
  }, [allPosts]);

  const likedPosts: Post[] = getLikedPosts(actions, postsByUri);
  const comments: AgentAction[] = getCommentActions(actions);

  return (
    <div className="bg-white border border-beige-300 rounded-lg p-4 space-y-3">
      <div className="font-medium text-beige-900">{agent.name}</div>
      <div className="text-sm text-beige-600">{agent.handle}</div>

      <CollapsibleSection
        title="Agent Metadata"
        isOpen={expandedSections.metadata}
        onToggle={() => toggleSection('metadata', setExpandedSections)}
      >
        <div className="p-3 bg-beige-50 rounded space-y-2 text-sm">
          <div>
            <span className="font-medium text-beige-800">Name:</span>{' '}
            <span className="text-beige-900">{agent.name}</span>
          </div>
          <div>
            <span className="font-medium text-beige-800">Bio:</span>{' '}
            <span className="text-beige-900">{agent.bio}</span>
          </div>
          <div>
            <span className="font-medium text-beige-800">Generated Bio:</span>{' '}
            <span className="text-beige-900">{agent.generatedBio}</span>
          </div>
          <div>
            <span className="font-medium text-beige-800">Followers:</span>{' '}
            <span className="text-beige-900">{agent.followers.toLocaleString()}</span>
          </div>
          <div>
            <span className="font-medium text-beige-800">Following:</span>{' '}
            <span className="text-beige-900">{agent.following.toLocaleString()}</span>
          </div>
          <div>
            <span className="font-medium text-beige-800">Posts:</span>{' '}
            <span className="text-beige-900">{agent.postsCount.toLocaleString()}</span>
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Feed"
        count={feed.length}
        isOpen={expandedSections.feed}
        onToggle={() => toggleSection('feed', setExpandedSections)}
      >
        <div className="space-y-3">
          {feed.map((post) => (
            <PostCard key={post.uri} post={post} />
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Liked Posts"
        count={likedPosts.length}
        isOpen={expandedSections.likes}
        onToggle={() => toggleSection('likes', setExpandedSections)}
      >
        <div className="space-y-3">
          {likedPosts.length > 0 ? (
            likedPosts.map((post) => <PostCard key={post.uri} post={post} />)
          ) : (
            <div className="p-3 text-sm text-beige-600 bg-beige-50 rounded">
              No liked posts
            </div>
          )}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Comments"
        count={comments.length}
        isOpen={expandedSections.comments}
        onToggle={() => toggleSection('comments', setExpandedSections)}
      >
        <div className="space-y-2">
          {comments.length > 0 ? (
            comments.map((action) => (
              <div
                key={action.actionId}
                className="p-3 bg-beige-50 rounded space-y-2"
              >
                <div className="text-sm text-beige-900">
                  Comment on post{' '}
                  {action.postUri ? (
                    <span className="text-xs text-beige-600 font-mono break-all">
                      {action.postUri}
                    </span>
                  ) : (
                    <span className="text-xs text-beige-600">Unknown post</span>
                  )}
                </div>
                {action.postUri && postsByUri[action.postUri] ? (
                  <PostCard post={postsByUri[action.postUri]} />
                ) : (
                  <div className="p-3 text-sm text-beige-600 bg-white border border-beige-200 rounded">
                    Post preview unavailable
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="p-3 text-sm text-beige-600 bg-beige-50 rounded">
              No comments
            </div>
          )}
        </div>
      </CollapsibleSection>
    </div>
  );
}

function getLikedPosts(actions: AgentAction[], postsByUri: Record<string, Post>): Post[] {
  return actions
    .filter((action) => action.type === 'like' && Boolean(action.postUri))
    .map((action) => postsByUri[action.postUri ?? ''])
    .filter((post): post is Post => post !== undefined);
}

function getCommentActions(actions: AgentAction[]): AgentAction[] {
  return actions.filter((action) => action.type === 'comment');
}

function toggleSection(
  section: keyof ExpandedSectionsState,
  setExpandedSections: Dispatch<SetStateAction<ExpandedSectionsState>>,
): void {
  setExpandedSections((previousSections) => ({
    ...previousSections,
    [section]: !previousSections[section],
  }));
}
