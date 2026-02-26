"""Shared pytest fixtures for the full test suite."""

from __future__ import annotations

import os
import tempfile
import zlib
from collections.abc import Generator

import pytest
from faker import Faker

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.comment_repository import create_sqlite_comment_repository
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.follow_repository import create_sqlite_follow_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)
from db.repositories.like_repository import create_sqlite_like_repository
from db.repositories.metrics_repository import create_sqlite_metrics_repository
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.run_repository import create_sqlite_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from tests.factories.context import reset_faker, set_faker


@pytest.fixture
def sqlite_tx(temp_db):
    """Shared TransactionProvider for SQLite integration tests."""
    return SqliteTransactionProvider()


@pytest.fixture
def run_repo(temp_db, sqlite_tx):
    return create_sqlite_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def profile_repo(temp_db, sqlite_tx):
    return create_sqlite_profile_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def feed_post_repo(temp_db, sqlite_tx):
    return create_sqlite_feed_post_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def generated_feed_repo(temp_db, sqlite_tx):
    return create_sqlite_generated_feed_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def generated_bio_repo(temp_db, sqlite_tx):
    return create_sqlite_generated_bio_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def agent_repo(temp_db, sqlite_tx):
    return create_sqlite_agent_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def agent_bio_repo(temp_db, sqlite_tx):
    return create_sqlite_agent_bio_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def user_agent_profile_metadata_repo(temp_db, sqlite_tx):
    return create_sqlite_user_agent_profile_metadata_repository(
        transaction_provider=sqlite_tx
    )


@pytest.fixture
def metrics_repo(temp_db, sqlite_tx):
    return create_sqlite_metrics_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def like_repo(temp_db, sqlite_tx):
    return create_sqlite_like_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def comment_repo(temp_db, sqlite_tx):
    return create_sqlite_comment_repository(transaction_provider=sqlite_tx)


@pytest.fixture
def follow_repo(temp_db, sqlite_tx):
    return create_sqlite_follow_repository(transaction_provider=sqlite_tx)


@pytest.fixture(autouse=True)
def fake(request: pytest.FixtureRequest) -> Generator[Faker, None, None]:
    """Per-test seeded Faker instance for deterministic factory defaults."""
    node_id = request.node.nodeid
    seed = zlib.adler32(node_id.encode("utf-8"))
    faker = Faker()
    faker.seed_instance(seed)
    token = set_faker(faker)
    try:
        yield faker
    finally:
        reset_faker(token)


@pytest.fixture
def temp_db(monkeypatch: pytest.MonkeyPatch) -> Generator[str, None, None]:
    """Create a temporary SQLite database, initialize schema, then clean up.

    This fixture:
    - Creates a temp .sqlite file path
    - Ensures all SQLite consumers point at it (DB_PATH + SIM_DB_PATH)
    - Applies Alembic migrations via initialize_database()
    - Deletes the file on teardown
    """
    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    import db.adapters.sqlite.sqlite as sqlite_module
    from db.adapters.sqlite.sqlite import initialize_database

    monkeypatch.setattr(sqlite_module, "DB_PATH", temp_path)
    monkeypatch.setenv(sqlite_module.SIM_DB_PATH_ENV, temp_path)

    initialize_database()

    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
