import os

from atproto import Client
from dotenv import load_dotenv

load_dotenv()


class BlueskyClient:
    def __init__(self):
        self.client = Client()
        self.handle = os.getenv("BLUESKY_HANDLE")
        self.password = os.getenv("BLUESKY_PASSWORD")

        if not self.handle or not self.password:
            # Fallback for debugging
            print(
                f"Env vars - HANDLE: {self.handle}, PASS: {'*' * len(self.password) if self.password else 'None'}"
            )
            raise ValueError("BLUESKY_HANDLE and BLUESKY_PASSWORD must be set in .env.")

        self.client.login(self.handle, self.password)

    def get_profile(self, actor: str) -> dict | None:
        try:
            profile = self.client.get_profile(actor=actor)
            return profile.dict()
        except Exception as e:
            print(f"Error fetching profile for {actor}: {e}")
            return None

    def get_author_feed(self, actor: str, limit: int = 50) -> list[dict]:
        try:
            # get_author_feed returns a FeedViewPost list
            feed = self.client.get_author_feed(actor=actor, limit=limit)
            posts = []
            for item in feed.feed:
                posts.append(item.post.dict())
            return posts
        except Exception as e:
            print(f"Error fetching feed for {actor}: {e}")
            return []
