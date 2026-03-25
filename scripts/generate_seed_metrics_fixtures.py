from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulation.local_dev.derive_from_metadata import (
    derive_turn_and_run_metrics_from_fixtures,
)
from simulation.local_dev.seed_loader import FIXTURES_DIR
from simulation.local_dev.seed_metrics_fixtures import (
    metrics_payloads,
    parse_runs_and_turn_metadata,
)


def _render_metrics_json(fixtures_dir: Path) -> tuple[str, str]:
    runs, turn_metadata = parse_runs_and_turn_metadata(fixtures_dir)
    turn_metrics, run_metrics = derive_turn_and_run_metrics_from_fixtures(
        runs=runs,
        turn_metadata=turn_metadata,
    )
    turn_payload, run_payload = metrics_payloads(turn_metrics, run_metrics)
    return (
        json.dumps(turn_payload, indent=2, ensure_ascii=False) + "\n",
        json.dumps(run_payload, indent=2, ensure_ascii=False) + "\n",
    )


def _write_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate committed seed metrics fixtures from runs + turn_metadata."
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=FIXTURES_DIR,
        help="Path to seed fixtures directory (default: simulation/local_dev/seed_fixtures)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated outputs differ from committed fixtures.",
    )
    args = parser.parse_args()

    fixtures_dir = args.fixtures_dir.resolve()
    turn_metrics_path = fixtures_dir / "turn_metrics.json"
    run_metrics_path = fixtures_dir / "run_metrics.json"
    turn_rendered, run_rendered = _render_metrics_json(fixtures_dir)

    if args.check:
        turn_existing = (
            turn_metrics_path.read_text(encoding="utf-8")
            if turn_metrics_path.exists()
            else None
        )
        run_existing = (
            run_metrics_path.read_text(encoding="utf-8")
            if run_metrics_path.exists()
            else None
        )
        if turn_existing != turn_rendered or run_existing != run_rendered:
            print("Seed metrics fixtures are out of date.")
            print(
                "Run `uv run python scripts/generate_seed_metrics_fixtures.py` and commit changes."
            )
            return 1
        print("Seed metrics fixtures are up to date.")
        return 0

    turn_changed = _write_if_changed(turn_metrics_path, turn_rendered)
    run_changed = _write_if_changed(run_metrics_path, run_rendered)
    if turn_changed or run_changed:
        print("Generated seed metrics fixtures.")
    else:
        print("Seed metrics fixtures already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
