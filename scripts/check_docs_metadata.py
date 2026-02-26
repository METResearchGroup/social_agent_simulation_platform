#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import yaml

DEFAULT_DOC_DIRS = (Path("docs/runbooks"), Path("docs/plans"))


def parse_front_matter(text: str) -> tuple[dict[str, object], list[str]]:
    """Parse front matter from the leading YAML block.

    Returns the parsed mapping and a list of errors.
    """
    lines = text.splitlines()
    errors: list[str] = []
    if not lines or lines[0].strip() != "---":
        return {}, ["Missing leading YAML front matter (`---`)."]

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, ["Front matter not closed with `---`."]

    front = "\n".join(lines[1:closing_index])
    try:
        parsed = yaml.safe_load(front) or {}
    except yaml.YAMLError as exc:
        errors.append(f"Failed to parse YAML: {exc}")
        return {}, errors

    if not isinstance(parsed, dict):
        errors.append("YAML front matter must be a mapping/object.")
        return {}, errors

    return parsed, errors


def validate_metadata(path: Path) -> list[str]:
    """Return a list of validation errors for a single markdown file."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"Unable to read file: {exc}"]

    meta, errors = parse_front_matter(text)
    if errors:
        return errors

    issues: list[str] = []

    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        issues.append("`description` is missing or not a non-empty string.")

    tags = meta.get("tags")
    if not isinstance(tags, list):
        issues.append("`tags` is missing or not a YAML list.")
    elif any(not isinstance(tag, str) for tag in tags):
        issues.append("`tags` must be a list of strings.")

    return issues


def collect_markdown_files(
    paths: Sequence[Path], exclude: Sequence[Path]
) -> list[Path]:
    files: list[Path] = []
    normalized_excludes = {p.resolve() for p in exclude}

    def should_skip(target: Path) -> bool:
        return any(target.resolve().is_relative_to(exc) for exc in normalized_excludes)

    for path in paths:
        if path.is_file() and path.suffix.lower() == ".md":
            if not should_skip(path):
                files.append(path)
            continue

        if path.is_dir():
            for sub in sorted(path.rglob("*.md")):
                if not should_skip(sub):
                    files.append(sub)
            continue

        # allow glob expressions by falling back to matching resolved path
        resolved = path
        if not resolved.exists() and "*" in str(path):
            for sub in sorted(Path(".").glob(str(path))):
                if sub.is_file() and sub.suffix.lower() == ".md":
                    if not should_skip(sub):
                        files.append(sub)

    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that docs/runbooks and docs/plans Markdown files include description+tags."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Explicit files/directories to check (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        action="append",
        type=Path,
        default=[],
        help="Paths to exclude (relative to repo root).",
    )

    args = parser.parse_args()

    if args.paths:
        targets = args.paths
    else:
        targets = DEFAULT_DOC_DIRS

    to_check = collect_markdown_files(targets, args.exclude)
    if not to_check:
        print("No Markdown files matched the docs metadata validator.")
        return 0

    failures: dict[Path, list[str]] = {}
    for path in to_check:
        errs = validate_metadata(path)
        if errs:
            failures[path] = errs

    if failures:
        print("Docs metadata validation failed:")
        for path, errs in failures.items():
            print(f"\n{path}:")
            for err in errs:
                print(f"  - {err}")
        return 1

    print("Docs metadata validation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
