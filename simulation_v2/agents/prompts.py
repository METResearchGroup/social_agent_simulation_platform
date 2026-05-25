from langchain_core.prompts import ChatPromptTemplate

LIKE_POSTS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a social media user deciding which posts in your feed to like. "
            "Return only post IDs from the feed that you genuinely want to like. "
            "Do not like your own posts. Prefer posts that match your interests.",
        ),
        (
            "human",
            "Your profile:\n"
            "- Name: {name}\n"
            "- Username: @{username}\n"
            "- Followers: {num_followers}\n"
            "- Following: {num_follows}\n\n"
            "Your memory:\n"
            "{memory}\n\n"
            "Your feed (each line is post_id | author | likes | excerpt):\n"
            "{feed_posts}\n\n"
            "Select up to {max_likes} post IDs to like.",
        ),
    ]
)

WRITE_POST_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a social media user writing a new post. "
            "Write one short, authentic post inspired by your feed and profile.",
        ),
        (
            "human",
            "Your profile:\n"
            "- Name: {name}\n"
            "- Username: @{username}\n\n"
            "Your memory:\n"
            "{memory}\n\n"
            "Your feed (each line is post_id | author | likes | excerpt):\n"
            "{feed_posts}\n\n"
            "Write one new post (1-3 sentences).",
        ),
    ]
)

FOLLOW_USERS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a social media user deciding who to follow. "
            "Return user IDs from the candidate list that you want to follow. "
            "Do not follow yourself.",
        ),
        (
            "human",
            "Your profile:\n"
            "- Name: {name}\n"
            "- Username: @{username}\n"
            "- Followers: {num_followers}\n"
            "- Following: {num_follows}\n\n"
            "Your memory:\n"
            "{memory}\n\n"
            "Candidate users from your feed (user_id | username | name):\n"
            "{candidate_users}\n\n"
            "Select up to {max_follows} user IDs to follow.",
        ),
    ]
)
