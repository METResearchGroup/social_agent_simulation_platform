from __future__ import annotations

from simulation.core.models.profiles import BlueskyProfile
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class BlueskyProfileFactory(BaseFactory[BlueskyProfile]):
    @classmethod
    def create(
        cls,
        *,
        handle: str | None = None,
        did: str | None = None,
        display_name: str | None = None,
        bio: str | None = None,
        followers_count: int | None = None,
        follows_count: int | None = None,
        posts_count: int | None = None,
    ) -> BlueskyProfile:
        fake = get_faker()
        handle_value = (
            handle if handle is not None else f"{fake.user_name()}.bsky.social"
        )
        did_value = (
            did if did is not None else f"did:plc:{fake.uuid4().replace('-', '')}"
        )
        return BlueskyProfile(
            handle=handle_value,
            did=did_value,
            display_name=display_name if display_name is not None else fake.name(),
            bio=bio if bio is not None else fake.sentence(nb_words=10),
            followers_count=followers_count if followers_count is not None else 0,
            follows_count=follows_count if follows_count is not None else 0,
            posts_count=posts_count if posts_count is not None else 0,
        )
