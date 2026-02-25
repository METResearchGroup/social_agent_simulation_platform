from __future__ import annotations

from datetime import timezone

from tests.factories.context import get_faker


def _timestamp_utc_compact() -> str:
    fake = get_faker()
    dt = fake.date_time(tzinfo=timezone.utc)
    return dt.strftime("%Y_%m_%d-%H:%M:%S")


def _timestamp_utc_iso() -> str:
    fake = get_faker()
    dt = fake.date_time(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
