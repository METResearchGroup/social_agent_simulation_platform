"""App user model for Phase 2 identity persistence."""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class AppUser(BaseModel):
    """Internal app user record, synced from Supabase Auth JWT claims."""

    id: str
    auth_provider_id: str
    email: str
    display_name: str
    created_at: str
    last_seen_at: str

    @field_validator("auth_provider_id")
    @classmethod
    def validate_auth_provider_id(cls, v: str) -> str:
        """Validate that auth_provider_id is non-empty."""
        return validate_non_empty_string(v, "auth_provider_id")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate that the email is non-empty."""
        return validate_non_empty_string(v, "email")

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Validate that the display name is non-empty."""
        return validate_non_empty_string(v, "display_name")
