from __future__ import annotations

from pydantic import BaseModel

from simulation_v2.models.seed_data import LoadedSeedDataModel


class TurnInputsModel(BaseModel):
    seed_data: LoadedSeedDataModel
    total_turns: int
