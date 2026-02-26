"""Utilities for building safe SQL LIKE patterns from user input."""

LIKE_ESCAPE_CHAR: str = "\\"


def build_substring_like_pattern_from_user_query(user_query: str | None) -> str | None:
    """Convert a user search query into a safe, substring SQL LIKE pattern.

    Rules:
    - None/empty/whitespace returns None (meaning: no filtering).
    - Supports '*' (any-length) and '?' (single-character) wildcards.
    - Escapes SQL LIKE metacharacters so '%' and '_' are treated literally.
    - Enforces substring semantics by wrapping the translated query with '%'.

    Args:
        user_query: Raw query string from the client.

    Returns:
        A LIKE pattern string suitable for use with "LIKE ? ESCAPE '\\\\'",
        or None if no filtering should be applied.
    """
    if user_query is None:
        return None

    q: str = user_query.strip()
    if q == "":
        return None

    q = q.replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)
    q = q.replace("%", f"{LIKE_ESCAPE_CHAR}%")
    q = q.replace("_", f"{LIKE_ESCAPE_CHAR}_")

    q = q.replace("*", "%")
    q = q.replace("?", "_")

    return f"%{q}%"
