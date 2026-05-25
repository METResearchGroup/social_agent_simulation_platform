"""Manages memories of what an agent thinks about other users in the network.

Social media behavior is heavily relational: people like posts from familiar
accounts, follow accounts they repeatedly enjoy, ignore accounts they dislike,
and develop affinity through exposure. A pure content-memory system misses this.

Creates pairwise memories keyed by (viewer_user_id, target_user_id):

- repeated exposure count
- prior likes, prior follows
- topic overlap, affinity score
- last interaction
- short natural-language notes.
"""


def fetch_memory(_user) -> str:
    return ""
