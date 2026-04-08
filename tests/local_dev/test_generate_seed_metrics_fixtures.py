from __future__ import annotations

import shutil
from pathlib import Path

from scripts import generate_seed_metrics_fixtures
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.local_dev.seed_loader import FIXTURES_DIR
from simulation.local_dev.seed_metrics_fixtures import read_json_list


def _copy_fixtures_to_tmp(tmp_path: Path) -> Path:
    dest = tmp_path / "seed_fixtures"
    shutil.copytree(FIXTURES_DIR, dest)
    return dest


class TestGenerateSeedMetricsFixtures:
    def test_generate_writes_model_valid_json(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fixtures_dir = _copy_fixtures_to_tmp(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            [
                "generate_seed_metrics_fixtures.py",
                "--fixtures-dir",
                str(fixtures_dir),
            ],
        )

        rc = generate_seed_metrics_fixtures.main()
        assert rc == 0

        turn_metrics = [
            TurnMetrics.model_validate(item)
            for item in read_json_list(fixtures_dir / "turn_metrics.json")
        ]
        run_metrics = [
            RunMetrics.model_validate(item)
            for item in read_json_list(fixtures_dir / "run_metrics.json")
        ]
        assert len(turn_metrics) > 0
        assert len(run_metrics) > 0

    def test_check_passes_on_freshly_generated_fixtures(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fixtures_dir = _copy_fixtures_to_tmp(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            [
                "generate_seed_metrics_fixtures.py",
                "--fixtures-dir",
                str(fixtures_dir),
            ],
        )
        assert generate_seed_metrics_fixtures.main() == 0

        monkeypatch.setattr(
            "sys.argv",
            [
                "generate_seed_metrics_fixtures.py",
                "--fixtures-dir",
                str(fixtures_dir),
                "--check",
            ],
        )
        assert generate_seed_metrics_fixtures.main() == 0

    def test_check_fails_when_metrics_json_is_stale(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fixtures_dir = _copy_fixtures_to_tmp(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            [
                "generate_seed_metrics_fixtures.py",
                "--fixtures-dir",
                str(fixtures_dir),
            ],
        )
        assert generate_seed_metrics_fixtures.main() == 0

        # Break committed metrics content; --check must fail.
        broken = fixtures_dir / "turn_metrics.json"
        broken.write_text("[]\n", encoding="utf-8")
        monkeypatch.setattr(
            "sys.argv",
            [
                "generate_seed_metrics_fixtures.py",
                "--fixtures-dir",
                str(fixtures_dir),
                "--check",
            ],
        )
        assert generate_seed_metrics_fixtures.main() == 1
