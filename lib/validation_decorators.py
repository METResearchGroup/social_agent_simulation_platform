"""Decorators for validating function inputs.

These decorators are intended to reduce repetitive guard boilerplate while
keeping validation explicit at call boundaries (e.g. query services,
repositories, adapters).
"""

import asyncio
import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, Awaitable, ParamSpec, TypeAlias, TypeVar, overload

P = ParamSpec("P")
R = TypeVar("R")

# A validator spec describes which inputs to validate.
#
# Forms:
# - (validator, "param_name"): calls validator(value). If the validator returns
#   a non-None value, it replaces the parameter value (normalization).
# - (validator, ("a", "b", ...)): calls validator(a, b, ...). Return value is
#   ignored (raise-only / cross-field validation).
ValidatorSpec: TypeAlias = tuple[Callable[..., object], str | tuple[str, ...]]


@overload
def validate_inputs(
    *specs: ValidatorSpec,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


@overload
def validate_inputs(
    *specs: ValidatorSpec,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]: ...


def validate_inputs(
    *specs: ValidatorSpec,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Validate named inputs before calling a function.

    Each spec maps a validator to one or more parameter names. Validators are
    expected to raise (typically ValueError) on invalid input. For single-input
    validators, a non-None return value is treated as the normalized value and
    is rebound into the call.
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        sig = inspect.signature(func)

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                _apply_specs(bound=bound, specs=specs)
                return await func(*bound.args, **bound.kwargs)

            async_wrapper.__signature__ = sig  # type: ignore[attr-defined]
            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            _apply_specs(bound=bound, specs=specs)
            return func(*bound.args, **bound.kwargs)

        sync_wrapper.__signature__ = sig  # type: ignore[attr-defined]
        return sync_wrapper

    return decorator


def _apply_specs(
    *, bound: inspect.BoundArguments, specs: tuple[ValidatorSpec, ...]
) -> None:
    for validator, names in specs:
        if isinstance(names, str):
            _validate_one(bound=bound, validator=validator, param_name=names)
        else:
            _validate_many(bound=bound, validator=validator, param_names=names)


def _validate_one(
    *, bound: inspect.BoundArguments, validator: Callable[..., object], param_name: str
) -> None:
    value = bound.arguments[param_name]
    replacement = validator(value)
    if replacement is not None:
        bound.arguments[param_name] = replacement


def _validate_many(
    *,
    bound: inspect.BoundArguments,
    validator: Callable[..., object],
    param_names: tuple[str, ...],
) -> None:
    values = [bound.arguments[name] for name in param_names]
    validator(*values)
