"""Guard tests ensuring legacy simulation_v2 runtime paths stay deleted."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SIMULATION_V2_ROOT = REPO_ROOT / "simulation_v2"

DELETED_PATHS = [
    "simulation_v2/simulate_run.py",
    "simulation_v2/simulate_turn.py",
    "simulation_v2/legacy_feeds.py",
    "simulation_v2/load_seed_data.py",
    "simulation_v2/seed_data.py",
    "simulation_v2/agents",
    "simulation_v2/models",
]

FORBIDDEN_IMPORTS = [
    "simulation_v2.simulate_run",
    "simulation_v2.simulate_turn",
    "simulation_v2.legacy_feeds",
    "simulation_v2.load_seed_data",
    "simulation_v2.agents",
    "simulation_v2.models.seed_data",
    "simulation_v2.models.telemetry",
]


def _python_files_under_simulation_v2() -> list[Path]:
    return [path for path in SIMULATION_V2_ROOT.rglob("*.py") if path.is_file()]


@pytest.mark.parametrize("relative_path", DELETED_PATHS)
def test_deleted_path_does_not_exist(relative_path: str) -> None:
    assert not (REPO_ROOT / relative_path).exists()


@pytest.mark.parametrize("import_path", FORBIDDEN_IMPORTS)
def test_no_forbidden_imports_under_simulation_v2(import_path: str) -> None:
    matches: list[str] = []
    for path in _python_files_under_simulation_v2():
        text = path.read_text(encoding="utf-8")
        if import_path in text:
            matches.append(str(path.relative_to(REPO_ROOT)))
    assert not matches, f"Found forbidden import {import_path!r} in: {matches}"
