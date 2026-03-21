---
description: Optional audit SQL and orphan-row policy notes for feed_posts.author_agent_id migration e7f3a9c2d1b4.
tags:
  - migrations
  - sqlite
  - feed-posts
  - author-agent-id
---

# Post author_agent_id migration (implementation notes)

## Orphan `feed_posts` rows

Migration `e7f3a9c2d1b4_add_feed_posts_author_agent_id` backfills `author_agent_id` from `agent` using `feed_posts.author_handle = agent.handle` and **deletes** rows where no match exists.

Audit before upgrade on a copy:

```sql
SELECT COUNT(*) FROM feed_posts fp
WHERE NOT EXISTS (SELECT 1 FROM agent a WHERE a.handle = fp.author_handle);
```

## Post-upgrade check

```sql
SELECT COUNT(*) FROM feed_posts WHERE author_agent_id IS NULL;
```

Expected: `0`.
