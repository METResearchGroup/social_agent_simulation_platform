'use client';

import { Post } from '@/types';

interface PostCardProps {
  post: Post;
}

export default function PostCard({ post }: PostCardProps) {
  return (
    <div className="bg-white border border-beige-300 rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-medium text-beige-900">{post.authorDisplayName}</div>
          <div className="text-sm text-beige-600">{post.authorHandle}</div>
        </div>
        <div className="text-xs text-beige-500">
          {new Date(post.createdAt).toLocaleDateString()}
        </div>
      </div>
      <p className="text-sm text-beige-800 leading-relaxed">{post.text}</p>
      <div className="flex gap-4 text-xs text-beige-600 pt-2 border-t border-beige-200">
        <span>❤️ {post.likeCount}</span>
        <span>💬 {post.replyCount}</span>
        <span>🔄 {post.repostCount}</span>
        <span>🔖 {post.bookmarkCount}</span>
      </div>
    </div>
  );
}
