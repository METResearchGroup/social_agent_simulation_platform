import time

from ml_tooling.ner.model import NERModel


def timed_extract(ner_model, text, label):
    start = time.perf_counter()
    result = ner_model.extract_entities(text)
    elapsed = time.perf_counter() - start
    print(f"[{label}] ({elapsed:.4f}s)")
    print(result)
    print("\n\n")


def verify_diff_cases():
    start = time.perf_counter()
    ner_model = NERModel()
    print(f"[init] ({time.perf_counter() - start:.4f}s)\n\n")

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


def run_10000():
    start = time.perf_counter()
    ner_model = NERModel()
    for i in range(10000):
        ner_model.extract_entities("My name is Wolfgang and I live in Berlin")
    elapsed = time.perf_counter() - start
    print(f"10000 inferences took {elapsed}s")


if __name__ == "__main__":
    verify_diff_cases()
    run_10000()
