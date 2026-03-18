"""Simulation API router composition.

Aggregates resource-oriented route modules; keeps URL paths and response models stable.
"""

from fastapi import APIRouter, Depends

from simulation.api.dependencies.app_user import require_current_app_user
from simulation.api.routes.agents import router as agents_router
from simulation.api.routes.metadata import router as metadata_router
from simulation.api.routes.posts import router as posts_router
from simulation.api.routes.runs import router as runs_router

router = APIRouter(
    tags=["simulation"], dependencies=[Depends(require_current_app_user)]
)
router.include_router(runs_router)
router.include_router(agents_router)
router.include_router(metadata_router)
router.include_router(posts_router)
