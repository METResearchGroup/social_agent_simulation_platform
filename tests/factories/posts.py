from __future__ import annotations

from datetime import timezone

from simulation.core.models.posts import BlueskyFeedPost
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


def _timestamp_utc_iso() -> str:
    fake = get_faker()
    dt = fake.date_time(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _did_plc() -> str:
    fake = get_faker()
    return fake.uuid4().replace("-", "")[:20]


def _post_key() -> str:
    fake = get_faker()
    return fake.uuid4().replace("-", "")[:16]


class PostFactory(BaseFactory[BlueskyFeedPost]):
    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        uri: str | None = None,
        author_handle: str | None = None,
        author_display_name: str | None = None,
        text: str | None = None,
        like_count: int | None = None,
        bookmark_count: int | None = None,
        quote_count: int | None = None,
        reply_count: int | None = None,
        repost_count: int | None = None,
        created_at: str | None = None,
    ) -> BlueskyFeedPost:
        fake = get_faker()
        uri_value = (
            uri
            if uri is not None
            else f"at://did:plc:{_did_plc()}/app.bsky.feed.post/{_post_key()}"
        )
        author_handle_value = (
            author_handle
            if author_handle is not None
            else f"{fake.user_name()}.bsky.social"
        )
        author_display_name_value = (
            author_display_name if author_display_name is not None else fake.name()
        )
        text_value = text if text is not None else fake.paragraph(nb_sentences=2)
        like_count_value = (
            like_count if like_count is not None else fake.random_int(0, 2000)
        )
        bookmark_count_value = (
            bookmark_count if bookmark_count is not None else fake.random_int(0, 500)
        )
        quote_count_value = (
            quote_count if quote_count is not None else fake.random_int(0, 200)
        )
        reply_count_value = (
            reply_count if reply_count is not None else fake.random_int(0, 500)
        )
        repost_count_value = (
            repost_count if repost_count is not None else fake.random_int(0, 500)
        )
        created_at_value = (
            created_at if created_at is not None else _timestamp_utc_iso()
        )

        if id is None:
            return BlueskyFeedPost(
                id=uri_value,
                uri=uri_value,
                author_handle=author_handle_value,
                author_display_name=author_display_name_value,
                text=text_value,
                like_count=like_count_value,
                bookmark_count=bookmark_count_value,
                quote_count=quote_count_value,
                reply_count=reply_count_value,
                repost_count=repost_count_value,
                created_at=created_at_value,
            )

        return BlueskyFeedPost(
            id=id,
            uri=uri_value,
            author_handle=author_handle_value,
            author_display_name=author_display_name_value,
            text=text_value,
            like_count=like_count_value,
            bookmark_count=bookmark_count_value,
            quote_count=quote_count_value,
            reply_count=reply_count_value,
            repost_count=repost_count_value,
            created_at=created_at_value,
        )
