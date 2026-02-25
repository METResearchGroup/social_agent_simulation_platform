from __future__ import annotations

from contextvars import ContextVar, Token

from faker import Faker

_FAKER: ContextVar[Faker | None] = ContextVar("tests_factories_faker", default=None)


def set_faker(fake: Faker) -> Token[Faker | None]:
    """Set the per-test Faker instance used by factories."""
    return _FAKER.set(fake)


def reset_faker(token: Token[Faker | None]) -> None:
    """Reset the per-test Faker instance back to the previous value."""
    _FAKER.reset(token)


def get_faker() -> Faker:
    """Return the per-test Faker instance.

    Raises:
        RuntimeError: If called outside pytest without the autouse `fake` fixture.
    """
    fake = _FAKER.get()
    if fake is None:
        raise RuntimeError(
            "tests.factories.get_faker() called without a configured Faker instance. "
            "Ensure pytest is running with the autouse `fake` fixture from "
            "tests/conftest.py."
        )
    return fake
