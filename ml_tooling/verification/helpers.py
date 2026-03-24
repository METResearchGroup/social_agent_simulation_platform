import time
from collections.abc import Callable


def track_init_time(model_class: type) -> object:
    start = time.perf_counter()
    model = model_class()
    print(f"[init] ({time.perf_counter() - start:.4f}s)\n\n")  # noqa: T201
    return model


def run_same_prompt(inference_func: Callable, prompt: str, iters: int) -> float:
    start = time.perf_counter()
    for _ in range(iters):
        inference_func(prompt)
    return time.perf_counter() - start
