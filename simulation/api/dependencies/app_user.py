"""FastAPI dependency that resolves and upserts current app_user from JWT claims."""

from fastapi import Depends, HTTPException, Request

from simulation.api.dependencies.auth import require_auth
from simulation.core.models.app_user import AppUser


def require_current_app_user(
    request: Request,
    claims: dict = Depends(require_auth),
) -> AppUser:
    """Verify auth, upsert app_user from JWT claims, attach to request.state, and return it."""
    auth_provider_id = claims["sub"]
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=400, detail="Supabase JWT must include a non-empty email claim."
        )

    user_metadata = claims.get("user_metadata") or {}
    display_name = user_metadata.get("full_name") or email

    if not display_name:
        raise HTTPException(
            status_code=400,
            detail="Display name must be present in the Supabase claims.",
        )

    repo = request.app.state.app_user_repository
    app_user = repo.upsert_from_auth(
        auth_provider_id=auth_provider_id,
        email=email,
        display_name=display_name,
    )
    request.state.current_app_user = app_user
    return app_user
