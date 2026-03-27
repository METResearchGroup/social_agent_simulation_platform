import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


# helper functions for printing tables
def _get_table_config(columns: list[str], data_rows: list[list[Any]], padding: int = 2):
    widths = []
    for i, col_name in enumerate(columns):
        max_data_len = max((len(str(row[i])) for row in data_rows), default=0)
        widths.append(max(len(col_name), max_data_len))

    sep = "+" + "+".join("-" * (w + padding) for w in widths) + "+"
    template = "|" + "|".join(f" {{:<{w}}} " for w in widths) + "|"

    return {"sep": sep, "template": template, "columns": columns, "widths": widths}


def _print_table_header(config: dict, title: str | None = None):
    if title:
        print(f"[{title}]")  # noqa: T201
    print(config["sep"])  # noqa: T201
    print(config["template"].format(*config["columns"]))  # noqa: T201
    print(config["sep"])  # noqa: T201


def _print_table_rows(config: dict, rows: list[list[Any]]):
    for row in rows:
        formatted_row = [str(item) for item in row]
        print(config["template"].format(*formatted_row))  # noqa: T201


def _print_table_footer(config: dict):
    print(config["sep"])  # noqa: T201
    print()  # noqa: T201


def _prepare_table_rows(
    text: str, col_names: list[str], col_values: list[tuple[Any, ...]], wrap_width: int
) -> list[list[str]]:
    text_lines = [text[i : i + wrap_width] for i in range(0, len(text), wrap_width)]
    n_rows = max(len(text_lines), len(col_values))
    combined_rows = []

    for i in range(n_rows):
        t_line = text_lines[i] if i < len(text_lines) else ""
        v_vals = col_values[i] if i < len(col_values) else [""] * len(col_names)
        combined_rows.append([t_line, *v_vals])

    return combined_rows


def _display_eval_results(results: list[tuple[int, float]]):
    cols = ["iters", "total (s)", "iters/sec"]
    data = [
        [n, f"{elapsed:.4f}", f"{n / elapsed:.2f}" if elapsed > 0 else "inf"]
        for n, elapsed in results
    ]

    config = _get_table_config(cols, data)
    _print_table_header(config)
    _print_table_rows(config, data)
    _print_table_footer(config)


def _run_same_prompt(inference_func: Callable, prompt: str, iters: int) -> float:
    start = time.perf_counter()
    for _ in range(iters):
        inference_func(prompt)
    return time.perf_counter() - start


# public functions for use in examples_tests
def evaluate_model_performance(inference_func: Callable, prompt: str) -> None:
    counts = [1, 10, 100, 1000, 10000]
    results = [(n, _run_same_prompt(inference_func, prompt, n)) for n in counts]
    _display_eval_results(results)


def print_table(
    case_name: str,
    text: str,
    col_names: list[str],
    col_values: list[tuple[Any, ...]],
    wrap_width: int = 30,
) -> None:
    """
    Prints a formatted table with info about a model's output for a given test case.

    Args:
        case_name: The title (if exists) displayed above the table.
        text: The string to be placed in the 'text' column (wrapped).
        col_names: A list of headers for the data columns, not including the 'text' column.
        col_values: A list of tuples containing the row values for the additional columns.
        wrap_width: The character limit per line for the 'text' column.
    """
    combined_rows = _prepare_table_rows(text, col_names, col_values, wrap_width)
    all_cols = ["text"] + col_names
    config = _get_table_config(all_cols, combined_rows)

    _print_table_header(config, title=case_name)
    _print_table_rows(config, combined_rows)
    _print_table_footer(config)


def track_runtime(should_print: bool) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                elapsed: float = time.perf_counter() - start
                if should_print:
                    print(f"[{function.__name__}] ({elapsed:.4f}s)\n")  # noqa: T201

        return wrapper

    return decorator


@track_runtime(should_print=True)
def init_model(model_class: type[T]) -> T:
    return model_class()
