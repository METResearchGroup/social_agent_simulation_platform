"""Pydantic row models for generations and proposed actions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

ProposedActionRecordKind = Literal["validated", "rejected"]
RejectionStage = Literal["llm_schema", "business_rules"]


class GenerationRecord(BaseModel):
    generation_id: str
    run_id: str
    turn_id: str
    user_id: str
    action_type: str
    parsed_response_json: dict[str, Any] | None = None
    raw_response_json: dict[str, Any] | None = None
    status: str
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    created_at: str
    error: str | None = None


class LlmProposedActionRecord(BaseModel):
    llm_proposed_action_id: str
    generation_id: str
    run_id: str
    turn_id: str
    user_id: str
    action_type: str
    target_type: str | None = None
    target_id: str | None = None
    target_content: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: str


class ProposedActionRecord(BaseModel):
    action_id: str
    record_kind: ProposedActionRecordKind
    generation_id: str | None = None
    run_id: str
    turn_id: str
    user_id: str
    action_type: str
    target_type: str | None = None
    target_id: str | None = None
    target_content: str | None = None
    filter_id: str | None = None
    filter_reason: str | None = None
    rejection_stage: RejectionStage | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: str
