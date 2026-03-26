"""Tests for Feature Extraction API health endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ml_tooling.api.main import app


class TestHealthEndpoint:
    def test_returns_ok_contract(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "feature-extraction"

    def test_includes_version_from_feature_extraction_version(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FEATURE_EXTRACTION_VERSION", "0.9.0-test")
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["version"] == "0.9.0-test"

    def test_version_prefers_feature_extraction_over_git_commit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FEATURE_EXTRACTION_VERSION", "from-fe")
        monkeypatch.setenv("GIT_COMMIT", "abc123")
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.json()["version"] == "from-fe"

    def test_version_falls_back_to_railway_git_commit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FEATURE_EXTRACTION_VERSION", raising=False)
        monkeypatch.delenv("GIT_COMMIT", raising=False)
        monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "sha-railway")
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.json()["version"] == "sha-railway"

    def test_version_prefers_git_commit_when_feature_extraction_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FEATURE_EXTRACTION_VERSION", raising=False)
        monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
        monkeypatch.setenv("GIT_COMMIT", "git-commit-only")
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["version"] == "git-commit-only"

    def test_version_omitted_when_no_envs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FEATURE_EXTRACTION_VERSION", raising=False)
        monkeypatch.delenv("GIT_COMMIT", raising=False)
        monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" not in data
