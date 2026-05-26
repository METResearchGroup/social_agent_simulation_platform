"""Progress toggle for simulation_v2 tests."""

from __future__ import annotations

import pytest

from simulation_v2.lib.decorators import no_progress


@pytest.fixture(autouse=True)
def disable_simulation_progress():
    with no_progress():
        yield
