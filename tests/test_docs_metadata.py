from pathlib import Path

import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from scripts.check_docs_metadata import collect_markdown_files, validate_metadata


def write_doc(tmp_path: Path, name: str, front_matter: str) -> Path:
    path = tmp_path / name
    path.write_text(front_matter, encoding="utf-8")
    return path


def build_front_matter(mapping: dict[str, object]) -> str:
    body = yaml.safe_dump(mapping, sort_keys=False).strip()
    return f"---\n{body}\n---\n\nContent\n"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    description=st.text(min_size=1),
    tags=st.lists(st.text(min_size=1), min_size=1),
)
def test_validate_metadata_accepts_good_front_matter(
    tmp_path: Path, description: str, tags: list[str]
) -> None:
    path = write_doc(
        tmp_path,
        "good.md",
        build_front_matter({"description": description, "tags": tags}),
    )

    assert validate_metadata(path) == []


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(tags=st.lists(st.text(min_size=1), min_size=1))
def test_validate_metadata_rejects_missing_description(
    tmp_path: Path, tags: list[str]
) -> None:
    path = write_doc(tmp_path, "missing.md", build_front_matter({"tags": tags}))

    errors = validate_metadata(path)
    assert any("description" in err for err in errors)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(description=st.text(min_size=1), tags=st.text())
def test_validate_metadata_rejects_non_list_tags(
    tmp_path: Path, description: str, tags: str
) -> None:
    path = write_doc(
        tmp_path,
        "bad_tags.md",
        build_front_matter({"description": description, "tags": tags}),
    )

    errors = validate_metadata(path)
    assert any("tags" in err for err in errors)


def test_validate_metadata_rejects_non_mapping_front_matter(tmp_path: Path) -> None:
    front = "---\n- item\n- other\n---\n"
    path = write_doc(tmp_path, "nonmapping.md", front)

    errors = validate_metadata(path)
    assert any("front matter" in err.lower() for err in errors)


def create_docs(tmp_path: Path, names: list[str]) -> list[Path]:
    base = tmp_path / "docs" / "runbooks"
    base.mkdir(parents=True)
    paths = []
    for name in names:
        path = base / name
        path.write_text(
            build_front_matter({"description": name, "tags": ["doc"]}),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def test_collect_markdown_files_walks_directories(tmp_path: Path) -> None:
    paths = create_docs(tmp_path, ["a.md", "b.md"])

    files = collect_markdown_files([tmp_path / "docs"], [])
    assert set(paths).issubset(set(files))


def test_collect_markdown_files_respects_exclude(tmp_path: Path) -> None:
    paths = create_docs(tmp_path, ["ok.md", "skip.md"])
    excluded = paths[1]

    files = collect_markdown_files([tmp_path / "docs"], [excluded])
    assert paths[0] in files and excluded not in files
