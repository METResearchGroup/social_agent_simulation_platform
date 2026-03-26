import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")


def run_same_prompt(inference_func: Callable, prompt: str, iters: int) -> float:
    start = time.perf_counter()
    for _ in range(iters):
        inference_func(prompt)
    return time.perf_counter() - start


def run_model_track_time(inference_func: Callable, prompt: str) -> None:
    counts = [1, 10, 100, 1000, 10000]
    results = [(n, run_same_prompt(inference_func, prompt, n)) for n in counts]

    col1, col2, col3 = "iters", "total (s)", "iters/sec"
    w1, w2, w3 = max(len(col1), 6), max(len(col2), 10), max(len(col3), 10)
    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"
    header = f"| {col1:<{w1}} | {col2:<{w2}} | {col3:<{w3}} |"

    print(sep)  # noqa: T201
    print(header)  # noqa: T201
    print(sep)  # noqa: T201
    for n, elapsed in results:
        throughput = n / elapsed if elapsed > 0 else float("inf")
        print(f"| {n:<{w1}} | {elapsed:<{w2}.4f} | {throughput:<{w3}.2f} |")  # noqa: T201
    print(sep)  # noqa: T201


def track_runtime(should_print: bool):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = function(*args, **kwargs)
            elapsed: float = time.perf_counter() - start
            if should_print:
                print(f"[{function.__name__}] ({elapsed:.4f}s)\n\n")  # noqa: T201

            return result

        return wrapper

    return decorator


@track_runtime(should_print=True)
def init_model(model_class: type[T]) -> T:
    return model_class()


def print_table(
    case_name: str,
    text: str,
    col_names: list[str],
    col_values: list[tuple[str, ...]],
    wrap_width: int = 40,
) -> None:
    w_text = max(len("text"), wrap_width)
    col_widths = [
        max(len(name), max((len(row[i]) for row in col_values), default=0))
        for i, name in enumerate(col_names)
    ]

    sep = (
        f"+{'-' * (w_text + 2)}+"
        + "+".join(f"{'-' * (w + 2)}" for w in col_widths)
        + "+"
    )
    header = (
        f"| {'text':<{w_text}} |"
        + "|".join(
            f" {name:<{w}} " for name, w in zip(col_names, col_widths, strict=True)
        )
        + "|"
    )

    text_lines = [text[i : i + wrap_width] for i in range(0, len(text), wrap_width)]

    print(f"[{case_name}]")  # noqa: T201
    print(sep)  # noqa: T201
    print(header)  # noqa: T201
    print(sep)  # noqa: T201

    n_rows = max(len(text_lines), len(col_values))
    for i in range(n_rows):
        text_line = text_lines[i] if i < len(text_lines) else ""
        if i < len(col_values):
            val_str = "|".join(
                f" {v:<{w}} " for v, w in zip(col_values[i], col_widths, strict=True)
            )
        else:
            val_str = "|".join(f" {'':{w}} " for w in col_widths)
        print(f"| {text_line:<{w_text}} |{val_str}|")  # noqa: T201

    print(sep)  # noqa: T201
    print()  # noqa: T201
