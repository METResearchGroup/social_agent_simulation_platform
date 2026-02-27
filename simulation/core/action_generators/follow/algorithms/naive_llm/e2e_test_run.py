"""E2E test: run naive LLM follow generator with real LLM (2-3 calls).

Requires OPENAI_API_KEY or provider key per ml_tooling LLM config.
"""

from lib.load_env_vars import EnvVarsContainer
from simulation.core.factories.action_generators.follow.naive_llm import (
    create_naive_llm_follow_generator,
)
from simulation.core.models.posts import Post, PostSource


def _post(
    uri: str,
    *,
    author_handle: str = "alice.bsky.social",
    text: str = "Sample post content",
    like_count: int = 10,
) -> Post:
    return Post(
        source=PostSource.BLUESKY,
        post_id=f"bluesky:{uri}",
        uri=uri,
        author_handle=author_handle,
        author_display_name="Alice",
        text=text,
        like_count=like_count,
        bookmark_count=0,
        quote_count=0,
        reply_count=0,
        repost_count=0,
        created_at="2024_02_15-14:30:00",
    )


def main() -> None:
    EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    generator = create_naive_llm_follow_generator()
    run_id = "e2e_run_1"

    candidates_1 = [
        _post(
            "post_1",
            author_handle="alice.bsky.social",
            text="Python tips",
            like_count=42,
        ),
        _post(
            "post_2", author_handle="bob.bsky.social", text="Rust vs Go", like_count=120
        ),
        _post(
            "post_3",
            author_handle="carol.bsky.social",
            text="Coffee culture",
            like_count=8,
        ),
    ]

    candidates_2 = [
        _post(
            "post_a",
            author_handle="dev.bsky.social",
            text="Systems programming",
            like_count=200,
        ),
        _post(
            "post_b",
            author_handle="designer.bsky.social",
            text="UI design",
            like_count=15,
        ),
    ]

    candidates_3 = [
        _post(
            "post_x",
            author_handle="writer.bsky.social",
            text="Creative writing tips",
            like_count=88,
        ),
        _post(
            "post_y",
            author_handle="photographer.bsky.social",
            text="Landscape photography",
            like_count=56,
        ),
    ]

    for i, candidates in enumerate([candidates_1, candidates_2, candidates_3], 1):
        print(f"\n--- Follow generator call {i} ---")
        result = generator.generate(
            candidates=candidates,
            run_id=run_id,
            turn_number=i,
            agent_handle="test_agent.bsky.social",
        )
        print(f"Follows generated: {len(result)}")
        for g in result:
            print(f"  - user_id={g.follow.user_id}, follow_id={g.follow.follow_id}")
        if result:
            print(f"Explanation sample: {result[0].explanation}")


if __name__ == "__main__":
    main()
