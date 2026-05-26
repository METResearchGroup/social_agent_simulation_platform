"""Repository insert/read helpers for simulation_v2 SQLite."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from simulation_v2.db.models import (
    AgentMemoryRecord,
    CommentRecord,
    EvalMetricRecord,
    EvalRunRecord,
    FeedPostView,
    FollowRecord,
    GeneratedFeedRecord,
    GenerationRecord,
    LikeRecord,
    LlmProposedActionRecord,
    MemoryDiffRecord,
    PostRecord,
    ProposedActionRecord,
    RunRecord,
    TurnRecord,
    UserRecord,
)


def _loads_json(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return json.loads(value)


def _dumps_json(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


class SimulationRepositories:
    def insert_run(self, record: RunRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, status, config_json, seed_metadata_json,
                created_at, started_at, finished_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.run_id,
                record.status,
                json.dumps(record.config_json),
                _dumps_json(record.seed_metadata_json),
                record.created_at,
                record.started_at,
                record.finished_at,
                record.error,
            ),
        )

    def get_run(self, run_id: str, conn: sqlite3.Connection) -> RunRecord | None:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return RunRecord(
            run_id=row["run_id"],
            status=row["status"],
            config_json=json.loads(row["config_json"]),
            seed_metadata_json=_loads_json(row["seed_metadata_json"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error=row["error"],
        )

    def insert_turn(self, record: TurnRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO turns (
                turn_id, run_id, turn_number, status,
                created_at, started_at, finished_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.turn_id,
                record.run_id,
                record.turn_number,
                record.status,
                record.created_at,
                record.started_at,
                record.finished_at,
                record.error,
            ),
        )

    def get_turn(self, turn_id: str, conn: sqlite3.Connection) -> TurnRecord | None:
        row = conn.execute(
            "SELECT * FROM turns WHERE turn_id = ?",
            (turn_id,),
        ).fetchone()
        if row is None:
            return None
        return TurnRecord(
            turn_id=row["turn_id"],
            run_id=row["run_id"],
            turn_number=row["turn_number"],
            status=row["status"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error=row["error"],
        )

    def insert_user(self, record: UserRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO users (
                user_id, run_id, name, email, username, profile_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.user_id,
                record.run_id,
                record.name,
                record.email,
                record.username,
                _dumps_json(record.profile_json),
                record.created_at,
            ),
        )

    def get_user(
        self, run_id: str, user_id: str, conn: sqlite3.Connection
    ) -> UserRecord | None:
        row = conn.execute(
            "SELECT * FROM users WHERE run_id = ? AND user_id = ?",
            (run_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return UserRecord(
            user_id=row["user_id"],
            run_id=row["run_id"],
            name=row["name"],
            email=row["email"],
            username=row["username"],
            profile_json=_loads_json(row["profile_json"]),
            created_at=row["created_at"],
        )

    def insert_post(self, record: PostRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO posts (
                post_id, run_id, author_id, content,
                created_at, created_at_turn, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.post_id,
                record.run_id,
                record.author_id,
                record.content,
                record.created_at,
                record.created_at_turn,
                _dumps_json(record.metadata_json),
            ),
        )

    def get_post(
        self, run_id: str, post_id: str, conn: sqlite3.Connection
    ) -> PostRecord | None:
        row = conn.execute(
            "SELECT * FROM posts WHERE run_id = ? AND post_id = ?",
            (run_id, post_id),
        ).fetchone()
        if row is None:
            return None
        return PostRecord(
            post_id=row["post_id"],
            run_id=row["run_id"],
            author_id=row["author_id"],
            content=row["content"],
            created_at=row["created_at"],
            created_at_turn=row["created_at_turn"],
            metadata_json=_loads_json(row["metadata_json"]),
        )

    def insert_like(self, record: LikeRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO likes (
                like_id, run_id, post_id, author_id,
                created_at, created_at_turn, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.like_id,
                record.run_id,
                record.post_id,
                record.author_id,
                record.created_at,
                record.created_at_turn,
                _dumps_json(record.metadata_json),
            ),
        )

    def get_like(self, like_id: str, conn: sqlite3.Connection) -> LikeRecord | None:
        row = conn.execute(
            "SELECT * FROM likes WHERE like_id = ?",
            (like_id,),
        ).fetchone()
        if row is None:
            return None
        return LikeRecord(
            like_id=row["like_id"],
            run_id=row["run_id"],
            post_id=row["post_id"],
            author_id=row["author_id"],
            created_at=row["created_at"],
            created_at_turn=row["created_at_turn"],
            metadata_json=_loads_json(row["metadata_json"]),
        )

    def insert_follow(self, record: FollowRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO follows (
                follow_id, run_id, follower_id, followee_id,
                created_at, created_at_turn, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.follow_id,
                record.run_id,
                record.follower_id,
                record.followee_id,
                record.created_at,
                record.created_at_turn,
                _dumps_json(record.metadata_json),
            ),
        )

    def get_follow(
        self, follow_id: str, conn: sqlite3.Connection
    ) -> FollowRecord | None:
        row = conn.execute(
            "SELECT * FROM follows WHERE follow_id = ?",
            (follow_id,),
        ).fetchone()
        if row is None:
            return None
        return FollowRecord(
            follow_id=row["follow_id"],
            run_id=row["run_id"],
            follower_id=row["follower_id"],
            followee_id=row["followee_id"],
            created_at=row["created_at"],
            created_at_turn=row["created_at_turn"],
            metadata_json=_loads_json(row["metadata_json"]),
        )

    def insert_comment(self, record: CommentRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO comments (
                comment_id, run_id, parent_post_id, author_id, content,
                created_at, created_at_turn, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.comment_id,
                record.run_id,
                record.parent_post_id,
                record.author_id,
                record.content,
                record.created_at,
                record.created_at_turn,
                _dumps_json(record.metadata_json),
            ),
        )

    def get_comment(
        self, comment_id: str, conn: sqlite3.Connection
    ) -> CommentRecord | None:
        row = conn.execute(
            "SELECT * FROM comments WHERE comment_id = ?",
            (comment_id,),
        ).fetchone()
        if row is None:
            return None
        return CommentRecord(
            comment_id=row["comment_id"],
            run_id=row["run_id"],
            parent_post_id=row["parent_post_id"],
            author_id=row["author_id"],
            content=row["content"],
            created_at=row["created_at"],
            created_at_turn=row["created_at_turn"],
            metadata_json=_loads_json(row["metadata_json"]),
        )

    def insert_agent_memory(
        self, record: AgentMemoryRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO agent_memories (
                run_id, user_id, preferences_json, episodic,
                personalized, social, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.run_id,
                record.user_id,
                _dumps_json(record.preferences_json),
                record.episodic,
                record.personalized,
                record.social,
                record.updated_at,
            ),
        )

    def get_agent_memory(
        self, run_id: str, user_id: str, conn: sqlite3.Connection
    ) -> AgentMemoryRecord | None:
        row = conn.execute(
            "SELECT * FROM agent_memories WHERE run_id = ? AND user_id = ?",
            (run_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return AgentMemoryRecord(
            run_id=row["run_id"],
            user_id=row["user_id"],
            preferences_json=_loads_json(row["preferences_json"]),
            episodic=row["episodic"],
            personalized=row["personalized"],
            social=row["social"],
            updated_at=row["updated_at"],
        )

    def insert_memory_diff(
        self, record: MemoryDiffRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO memory_diffs (
                memory_diff_id, run_id, turn_id, user_id,
                memory_type, content, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.memory_diff_id,
                record.run_id,
                record.turn_id,
                record.user_id,
                record.memory_type,
                record.content,
                record.created_at,
            ),
        )

    def get_memory_diff(
        self, memory_diff_id: str, conn: sqlite3.Connection
    ) -> MemoryDiffRecord | None:
        row = conn.execute(
            "SELECT * FROM memory_diffs WHERE memory_diff_id = ?",
            (memory_diff_id,),
        ).fetchone()
        if row is None:
            return None
        return MemoryDiffRecord(
            memory_diff_id=row["memory_diff_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            user_id=row["user_id"],
            memory_type=row["memory_type"],
            content=row["content"],
            created_at=row["created_at"],
        )

    def insert_generated_feed(
        self, record: GeneratedFeedRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO generated_feeds (
                feed_id, run_id, turn_id, user_id, algorithm,
                feed_post_ids_json, feed_posts_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.feed_id,
                record.run_id,
                record.turn_id,
                record.user_id,
                record.algorithm,
                json.dumps(record.feed_post_ids),
                json.dumps([post.model_dump() for post in record.feed_posts]),
                record.created_at,
            ),
        )

    def get_generated_feed(
        self, feed_id: str, conn: sqlite3.Connection
    ) -> GeneratedFeedRecord | None:
        row = conn.execute(
            "SELECT * FROM generated_feeds WHERE feed_id = ?",
            (feed_id,),
        ).fetchone()
        if row is None:
            return None
        feed_posts_raw = json.loads(row["feed_posts_json"])
        return GeneratedFeedRecord(
            feed_id=row["feed_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            user_id=row["user_id"],
            algorithm=row["algorithm"],
            feed_post_ids=json.loads(row["feed_post_ids_json"]),
            feed_posts=[FeedPostView.model_validate(item) for item in feed_posts_raw],
            created_at=row["created_at"],
        )

    def insert_generation(
        self, record: GenerationRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO generations (
                generation_id, run_id, turn_id, user_id, action_type,
                parsed_response_json, raw_response_json, status,
                latency_ms, prompt_tokens, completion_tokens, cost_usd,
                created_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.generation_id,
                record.run_id,
                record.turn_id,
                record.user_id,
                record.action_type,
                _dumps_json(record.parsed_response_json),
                _dumps_json(record.raw_response_json),
                record.status,
                record.latency_ms,
                record.prompt_tokens,
                record.completion_tokens,
                record.cost_usd,
                record.created_at,
                record.error,
            ),
        )

    def get_generation(
        self, generation_id: str, conn: sqlite3.Connection
    ) -> GenerationRecord | None:
        row = conn.execute(
            "SELECT * FROM generations WHERE generation_id = ?",
            (generation_id,),
        ).fetchone()
        if row is None:
            return None
        return GenerationRecord(
            generation_id=row["generation_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            user_id=row["user_id"],
            action_type=row["action_type"],
            parsed_response_json=_loads_json(row["parsed_response_json"]),
            raw_response_json=_loads_json(row["raw_response_json"]),
            status=row["status"],
            latency_ms=row["latency_ms"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            cost_usd=row["cost_usd"],
            created_at=row["created_at"],
            error=row["error"],
        )

    def insert_llm_proposed_action(
        self, record: LlmProposedActionRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO llm_proposed_actions (
                llm_proposed_action_id, generation_id, run_id, turn_id, user_id,
                action_type, target_type, target_id, target_content,
                metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.llm_proposed_action_id,
                record.generation_id,
                record.run_id,
                record.turn_id,
                record.user_id,
                record.action_type,
                record.target_type,
                record.target_id,
                record.target_content,
                _dumps_json(record.metadata_json),
                record.created_at,
            ),
        )

    def get_llm_proposed_action(
        self, llm_proposed_action_id: str, conn: sqlite3.Connection
    ) -> LlmProposedActionRecord | None:
        row = conn.execute(
            "SELECT * FROM llm_proposed_actions WHERE llm_proposed_action_id = ?",
            (llm_proposed_action_id,),
        ).fetchone()
        if row is None:
            return None
        return LlmProposedActionRecord(
            llm_proposed_action_id=row["llm_proposed_action_id"],
            generation_id=row["generation_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            user_id=row["user_id"],
            action_type=row["action_type"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            target_content=row["target_content"],
            metadata_json=_loads_json(row["metadata_json"]),
            created_at=row["created_at"],
        )

    def insert_proposed_action(
        self, record: ProposedActionRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO proposed_actions (
                action_id, record_kind, generation_id, run_id, turn_id, user_id,
                action_type, target_type, target_id, target_content,
                filter_id, filter_reason, rejection_stage, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.action_id,
                record.record_kind,
                record.generation_id,
                record.run_id,
                record.turn_id,
                record.user_id,
                record.action_type,
                record.target_type,
                record.target_id,
                record.target_content,
                record.filter_id,
                record.filter_reason,
                record.rejection_stage,
                _dumps_json(record.metadata_json),
                record.created_at,
            ),
        )

    def get_proposed_action(
        self, action_id: str, conn: sqlite3.Connection
    ) -> ProposedActionRecord | None:
        row = conn.execute(
            "SELECT * FROM proposed_actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()
        if row is None:
            return None
        return ProposedActionRecord(
            action_id=row["action_id"],
            record_kind=row["record_kind"],
            generation_id=row["generation_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            user_id=row["user_id"],
            action_type=row["action_type"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            target_content=row["target_content"],
            filter_id=row["filter_id"],
            filter_reason=row["filter_reason"],
            rejection_stage=row["rejection_stage"],
            metadata_json=_loads_json(row["metadata_json"]),
            created_at=row["created_at"],
        )

    def insert_eval_run(self, record: EvalRunRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO eval_runs (
                eval_run_id, run_id, turn_id, scope, plugin_name,
                status, created_at, finished_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.eval_run_id,
                record.run_id,
                record.turn_id,
                record.scope,
                record.plugin_name,
                record.status,
                record.created_at,
                record.finished_at,
                record.error,
            ),
        )

    def get_eval_run(
        self, eval_run_id: str, conn: sqlite3.Connection
    ) -> EvalRunRecord | None:
        row = conn.execute(
            "SELECT * FROM eval_runs WHERE eval_run_id = ?",
            (eval_run_id,),
        ).fetchone()
        if row is None:
            return None
        return EvalRunRecord(
            eval_run_id=row["eval_run_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            scope=row["scope"],
            plugin_name=row["plugin_name"],
            status=row["status"],
            created_at=row["created_at"],
            finished_at=row["finished_at"],
            error=row["error"],
        )

    def insert_eval_metric(
        self, record: EvalMetricRecord, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            INSERT INTO eval_metrics (
                eval_metric_id, eval_run_id, run_id, turn_id, plugin_name,
                metric_name, metric_value, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.eval_metric_id,
                record.eval_run_id,
                record.run_id,
                record.turn_id,
                record.plugin_name,
                record.metric_name,
                record.metric_value,
                _dumps_json(record.metadata_json),
                record.created_at,
            ),
        )

    def get_eval_metric(
        self, eval_metric_id: str, conn: sqlite3.Connection
    ) -> EvalMetricRecord | None:
        row = conn.execute(
            "SELECT * FROM eval_metrics WHERE eval_metric_id = ?",
            (eval_metric_id,),
        ).fetchone()
        if row is None:
            return None
        return EvalMetricRecord(
            eval_metric_id=row["eval_metric_id"],
            eval_run_id=row["eval_run_id"],
            run_id=row["run_id"],
            turn_id=row["turn_id"],
            plugin_name=row["plugin_name"],
            metric_name=row["metric_name"],
            metric_value=row["metric_value"],
            metadata_json=_loads_json(row["metadata_json"]),
            created_at=row["created_at"],
        )
