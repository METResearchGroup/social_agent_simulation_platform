from ml_tooling.ner.model import NERModel


def verify():
    ner_model = NERModel()

    test1 = "My name is Wolfgang and I live in Berlin"
    res = ner_model.extract_entities(test1)
    print(res)


if __name__ == "__main__":
    verify()
