"""Handle normalization utilities for agent and profile handles."""


def normalize_handle(raw: str) -> str:
    """Normalize a handle for storage and lookup.

    Strips whitespace, ensures @ prefix (adds if missing), and lowercases.
    Empty string after normalization raises ValueError.

    Args:
        raw: Raw handle string from user input or API.

    Returns:
        Normalized handle (e.g. "@user.bsky.social").

    Raises:
        ValueError: If the handle is empty after normalization.
    """
    s = raw.strip().lower()
    if not s:
        raise ValueError("Handle cannot be empty")
    if not s.startswith("@"):
        s = f"@{s}"
    return s
