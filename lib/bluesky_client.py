from atproto import Client

from lib.load_env_vars import EnvVarsContainer


class BlueskyClient:
    def __init__(self):
        self.client = Client()
        self.handle = EnvVarsContainer.get_env_var("BLUESKY_HANDLE", required=True)
        self.password = EnvVarsContainer.get_env_var("BLUESKY_PASSWORD", required=True)
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
