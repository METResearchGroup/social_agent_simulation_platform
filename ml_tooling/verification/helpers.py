import time


def track_init_time(model_class: type) -> object:
    start = time.perf_counter()
    model = model_class()
    print(f"[init] ({time.perf_counter() - start:.4f}s)\n\n")  # noqa: T201
    return model
