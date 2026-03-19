import time

from transformers import logging as transformers_logging

from ml_tooling.ner.classifier import NERModel

transformers_logging.set_verbosity_error()


def track_init_time():
    start = time.perf_counter()
    ner_model = NERModel()
    print(f"[init] ({time.perf_counter() - start:.4f}s)\n\n")  # noqa: T201
    ner_model.extract_entities("")

    return ner_model


def timed_extract(ner_model, text, label):
    start = time.perf_counter()
    result = ner_model.extract_entities(text)
    elapsed = time.perf_counter() - start
    print(f"[{label}] ({elapsed:.4f}s)")  # noqa: T201
    print(f"{result}\n")  # noqa: T201


def verify_diff_cases(ner_model):
    # "perfect" sequence
    timed_extract(ner_model, "My name is Wolfgang and I live in Berlin", "perfect")

    # all lowercase
    timed_extract(ner_model, "my name is wolfgang and i live in berlin", "lowercase")

    # zero entities
    timed_extract(
        ner_model,
        "this is a sentence and it is about to end right about now",
        "zero entities",
    )

    # recent entity
    timed_extract(
        ner_model,
        "I am Mayor Mamdani of New York and I just got elected very recently",
        "recent entity",
    )


def run_same_prompt(ner_model, iters):
    start = time.perf_counter()
    for _ in range(iters):
        ner_model.extract_entities("My name is Wolfgang and I live in Berlin")
    return time.perf_counter() - start


def run_model_track_time(ner_model):
    counts = [1, 10, 1000, 10000]
    results = [(n, run_same_prompt(ner_model, n)) for n in counts]

    col1, col2, col3 = "iters", "total (s)", "iters/sec"
    w1, w2, w3 = max(len(col1), 6), max(len(col2), 10), max(len(col3), 10)
    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"
    header = f"| {col1:<{w1}} | {col2:<{w2}} | {col3:<{w3}} |"

    print(sep)  # noqa: T201
    print(header)  # noqa: T201
    print(sep)  # noqa: T201
    for n, elapsed in results:
        throughput = n / elapsed
        print(f"| {n:<{w1}} | {elapsed:<{w2}.4f} | {throughput:<{w3}.2f} |")  # noqa: T201
    print(sep)  # noqa: T201


if __name__ == "__main__":
    ner_model = track_init_time()
    print("\n\n")  # noqa: T201

    verify_diff_cases(ner_model)
    print("\n\n")  # noqa: T201
    run_model_track_time(ner_model)
