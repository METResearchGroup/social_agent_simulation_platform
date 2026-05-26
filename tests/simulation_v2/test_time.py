"""Tests for simulation_v2 timestamp wrapper."""

from __future__ import annotations

import re

from lib import timestamp_utils
from simulation_v2 import time


class TestTimeWrapper:
    def test_exports_created_at_format(self) -> None:
        assert time.CREATED_AT_FORMAT == timestamp_utils.CREATED_AT_FORMAT
        assert time.CREATED_AT_FORMAT == "%Y_%m_%d-%H:%M:%S"

    def test_get_current_timestamp_matches_format(self) -> None:
        timestamp = time.get_current_timestamp()

        assert re.fullmatch(r"\d{4}_\d{2}_\d{2}-\d{2}:\d{2}:\d{2}", timestamp)
