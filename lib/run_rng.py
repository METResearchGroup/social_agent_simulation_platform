"""Run-scoped RNG for reproducible simulation behavior.

Provides deterministic random number generation per run and turn, using
stable seed derivation (SHA-256) across Python versions and processes.
"""

from __future__ import annotations

import hashlib
import random


def get_turn_rng(run_seed: int, turn_number: int) -> random.Random:
    """Build a deterministic RNG for a given run and turn.

    Uses SHA-256 for stable seed derivation, avoiding Python's built-in
    hash() which is not stable across PYTHONHASHSEED settings.

    Args:
        run_seed: The run's master seed (persisted on Run).
        turn_number: 0-indexed turn number; isolates per-turn randomness.

    Returns:
        A seeded random.Random instance for this run+turn.
    """
    digest = hashlib.sha256(
        f"{run_seed}_{turn_number}".encode(encoding="utf-8")
    ).hexdigest()
    turn_seed = int(digest[:16], 16)
    return random.Random(turn_seed)
