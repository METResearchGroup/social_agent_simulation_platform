"""E2E test: run naive LLM like generator with real LLM (2-3 calls).

Requires OPENAI_API_KEY or provider key per ml_tooling LLM config.
"""

from lib.load_env_vars import EnvVarsContainer
from simulation.core.factories.action_generators.like.naive_llm import (
    create_naive_llm_like_generator,
)
from simulation.core.models.posts import BlueskyFeedPost


def _post(
    post_id: str,
    *,
    author_handle: str = "alice.bsky.social",
    text: str = "Sample post content",
    like_count: int = 10,
) -> BlueskyFeedPost:
    return BlueskyFeedPost(
        id=post_id,
        uri=post_id,
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
    generator = create_naive_llm_like_generator()
    run_id = "e2e_run_1"

    candidates_1 = [
        _post("post_1", text="Just finished a great book on Python!", like_count=42),
        _post("post_2", text="Beautiful sunset today", like_count=120),
        _post("post_3", text="New coffee shop opened downtown", like_count=8),
    ]

    candidates_2 = [
        _post("post_a", text="Rust is awesome for systems programming", like_count=200),
        _post("post_b", text="Pizza night with friends", like_count=15),
    ]

    candidates_3 = [
        _post(
            "post_x",
            author_handle="dev.bsky.social",
            text="TIL: async/await simplifies concurrent code",
            like_count=88,
        ),
        _post(
            "post_y",
            author_handle="designer.bsky.social",
            text="Minimalist UI design principles",
            like_count=56,
        ),
    ]

    for i, candidates in enumerate([candidates_1, candidates_2, candidates_3], 1):
        print(f"\n--- Like generator call {i} ---")
        result = generator.generate(
            candidates=candidates,
            run_id=run_id,
            turn_number=i,
            agent_handle="test_agent.bsky.social",
        )
        print(f"Likes generated: {len(result)}")
        for g in result:
            print(f"  - post_id={g.like.post_id}, like_id={g.like.like_id}")
        if result:
            print(f"Explanation sample: {result[0].explanation}")


if __name__ == "__main__":
    main()
