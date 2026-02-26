"""Gateway settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GatewaySettings:
    upstream_base_url: str
    timeout_seconds: float
    allowed_origins_raw: str

    @classmethod
    def from_env(cls) -> "GatewaySettings":
        upstream = os.environ.get("GATEWAY_UPSTREAM_BASE_URL", "").strip().rstrip("/")
        if not upstream:
            raise RuntimeError("GATEWAY_UPSTREAM_BASE_URL must be set")

        timeout_raw = os.environ.get("GATEWAY_TIMEOUT_SECONDS", "60").strip()
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise RuntimeError(
                f"GATEWAY_TIMEOUT_SECONDS must be a number, got: {timeout_raw!r}"
            ) from exc

        allowed_origins_raw = os.environ.get(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        )
        return cls(
            upstream_base_url=upstream,
            timeout_seconds=timeout,
            allowed_origins_raw=allowed_origins_raw,
        )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins_raw.split(",")
            if origin.strip()
        ]
