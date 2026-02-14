"""For each profile in the database, generate an AI-generated bio
to use for the agent, and save to the database."""

import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from db.adapters.sqlite.sqlite import initialize_database
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from lib.langfuse_telemetry import get_langfuse_client, log_llm_request
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile

GENERATE_BIO_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert at creating concise and accurate bios
    for users on social media.

    Your task is to create a bio that captures the essence of a person based on
    their profile information and sample posts. The bio should be:

    - Comprehensive, 1-2 paragraphs.
    - Reinforced by specific examples and evidence.
    - Capture their personality, interests, and communication style.
    - Be suitable for use in a social media agent simulation.
    - Written in third person
    """,
        ),
        (
            "human",
            """Create a bio for this person:

    Profile Information:
    - Display Name: {display_name}
    - Handle: @{handle}
    - Current Bio: {current_bio}
    - Followers: {followers_count:,}
    - Following: {follows_count:,}
    - Total Posts: {posts_count:,}

    Sample Posts (recent activity):
    {posts_sample}

    Generate a comprehensive bio that captures this person's personality and interests:
    """,
        ),
    ]
)

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set")

MAX_POSTS_SAMPLE = 20

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
langfuse_client = get_langfuse_client()


def get_posts_sample(
    posts: list[BlueskyFeedPost], max_posts: int = MAX_POSTS_SAMPLE
) -> str:
    """Get a sample of posts formatted for the prompt.

    Args:
        posts: List of posts
        max_posts: Maximum number of posts to include

    Returns:
        Formatted string of post samples
    """
    if not posts:
        return "No posts available."

    sample_posts = posts[:max_posts]
    formatted = []
    for i, post in enumerate(sample_posts, 1):
        # Truncate long posts
        text = post.text[:200] + "..." if len(post.text) > 200 else post.text
        formatted.append(f"{i}. {text}")

    return "\n".join(formatted)


def generate_bio_for_profile(
    profile: BlueskyProfile, posts: list[BlueskyFeedPost]
) -> str:
    """Generate a bio for a profile using Langchain.

    Args:
        profile: BlueskyProfile to generate bio for
        posts: List of posts by this profile
        llm: Langchain LLM instance

    Returns:
        Generated bio string
    """
    posts_sample = get_posts_sample(posts)

    prompt = GENERATE_BIO_PROMPT.format_messages(
        display_name=profile.display_name,
        handle=profile.handle,
        current_bio=profile.bio,
        followers_count=profile.followers_count,
        follows_count=profile.follows_count,
        posts_count=profile.posts_count,
        posts_sample=posts_sample,
    )

    try:
        response = llm.invoke(prompt)
        if not isinstance(response.content, str):
            raise ValueError(
                f"Expected string response from LLM, got {type(response.content).__name__}"
            )
        generated_bio = response.content.strip()
        log_llm_request(
            langfuse_client,
            model="gpt-4o-mini",
            input_data={"profile_handle": profile.handle},
            output=generated_bio,
            metadata={"display_name": profile.display_name, "num_posts": len(posts)},
        )

        return generated_bio
    except Exception as e:
        raise ValueError(f"Error generating bio for {profile.handle}: {e}")


def main():
    initialize_database()
    print("Reading profiles and feed posts from database...")
    profile_repo = create_sqlite_profile_repository()
    feed_post_repo = create_sqlite_feed_post_repository()
    generated_bio_repo = create_sqlite_generated_bio_repository()
    profiles: list[BlueskyProfile] = profile_repo.list_profiles()
    feed_posts: list[BlueskyFeedPost] = feed_post_repo.list_all_feed_posts()
    posts_by_author: dict[str, list[BlueskyFeedPost]] = {}
    for post in feed_posts:
        posts_by_author.setdefault(post.author_handle, []).append(post)

    print("Generating bios for profiles...")
    for i, profile in enumerate(profiles, 1):
        print(f"Generating bio for profile {i} of {len(profiles)}...")
        posts = posts_by_author[profile.handle]
        generated_bio_text: str = generate_bio_for_profile(profile, posts)
        from simulation.core.models.generated.base import GenerationMetadata

        generated_bio = GeneratedBio(
            handle=profile.handle,
            generated_bio=generated_bio_text,
            metadata=GenerationMetadata(
                model_used="gpt-4o-mini",
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
        generated_bio_repo.create_or_update_generated_bio(generated_bio)
        print(f"Generated bio for {profile.handle}: {generated_bio_text}")

    print("All bios generated and written to database.")
    print("Reading all generated bios from database...")
    generated_bios: list[GeneratedBio] = generated_bio_repo.list_all_generated_bios()
    print(f"Found {len(generated_bios)} generated bios.")


if __name__ == "__main__":
    main()
