from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseFactory(ABC, Generic[T]):
    """Base factory providing a common create_batch implementation."""

    @classmethod
    @abstractmethod
    def create(cls, **kwargs: object) -> T:
        raise NotImplementedError

    @classmethod
    def create_batch(cls, n: int, **kwargs: object) -> list[T]:
        if n < 0:
            raise ValueError(f"n must be >= 0, got {n}")
        return [cls.create(**kwargs) for _ in range(n)]
