"""Memory service orchestration for prompts, diffs, and apply."""

from __future__ import annotations

from collections import defaultdict

from simulation_v2.db.models import (
    AgentMemoryRecord,
    MemoryDiffRecord,
    ProposedActionRecord,
)
from simulation_v2.ids import new_memory_diff_id
from simulation_v2.memory.episodic import (
    append_episodic,
    build_episodic_diff_content,
)
from simulation_v2.memory.personalized import (
    append_personalized,
    build_personalized_diff_content,
)
from simulation_v2.memory.social import append_social, build_social_diff_content
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.state import TurnStateSnapshot


def fetch_memory_for_prompt(memory: AgentMemoryRecord | None) -> str:
    episodic = memory.episodic if memory is not None else ""
    personalized = memory.personalized if memory is not None else ""
    social = memory.social if memory is not None else ""
    return f"""

    Episodic memory: experiences you've had recently
    ```markdown
    {episodic or ""}
    ```

    Personalized profile memory: A list of the agent's interests, liked/disliked topics, posting style, favorite accounts, political/technical/social tendencies and recent mood.

    ```markdown
    {personalized or ""}
    ```

    Social relationships memory: What the agent thinks about other users in the network.

    ```markdown
    {social or ""}
    ```
    """


def build_memory_diffs(
    validated_actions: list[ProposedActionRecord],
    snapshot: TurnStateSnapshot,
) -> list[MemoryDiffRecord]:
    if not validated_actions:
        return []

    actions_by_user: dict[str, list[ProposedActionRecord]] = defaultdict(list)
    for action in validated_actions:
        actions_by_user[action.user_id].append(action)

    memory_diffs: list[MemoryDiffRecord] = []
    created_at = get_current_timestamp()

    for user_id in sorted(actions_by_user):
        user_actions = actions_by_user[user_id]
        turn_number = snapshot.turn_number

        episodic_content = build_episodic_diff_content(turn_number, user_actions)
        if episodic_content is not None:
            memory_diffs.append(
                MemoryDiffRecord(
                    memory_diff_id=new_memory_diff_id(),
                    run_id=snapshot.run_id,
                    turn_id=snapshot.turn_id,
                    user_id=user_id,
                    memory_type="episodic",
                    content=episodic_content,
                    created_at=created_at,
                )
            )

        personalized_content = build_personalized_diff_content(
            turn_number, user_actions
        )
        if personalized_content is not None:
            memory_diffs.append(
                MemoryDiffRecord(
                    memory_diff_id=new_memory_diff_id(),
                    run_id=snapshot.run_id,
                    turn_id=snapshot.turn_id,
                    user_id=user_id,
                    memory_type="personalized",
                    content=personalized_content,
                    created_at=created_at,
                )
            )

        social_content = build_social_diff_content(turn_number, user_actions)
        if social_content is not None:
            memory_diffs.append(
                MemoryDiffRecord(
                    memory_diff_id=new_memory_diff_id(),
                    run_id=snapshot.run_id,
                    turn_id=snapshot.turn_id,
                    user_id=user_id,
                    memory_type="social",
                    content=social_content,
                    created_at=created_at,
                )
            )

    return memory_diffs


def apply_memory_diff(
    current: AgentMemoryRecord,
    diff: MemoryDiffRecord,
) -> AgentMemoryRecord:
    updated_at = get_current_timestamp()
    if diff.memory_type == "episodic":
        return current.model_copy(
            update={
                "episodic": append_episodic(current.episodic, diff.content),
                "updated_at": updated_at,
            }
        )
    if diff.memory_type == "personalized":
        return current.model_copy(
            update={
                "personalized": append_personalized(current.personalized, diff.content),
                "updated_at": updated_at,
            }
        )
    if diff.memory_type == "social":
        return current.model_copy(
            update={
                "social": append_social(current.social, diff.content),
                "updated_at": updated_at,
            }
        )
    raise ValueError(f"Unsupported memory type {diff.memory_type!r}")
