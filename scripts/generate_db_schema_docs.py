#!/usr/bin/env python3
"""Generate versioned DB schema documentation from Alembic migrations at HEAD.

This repo uses Alembic migrations to define the SQLite schema (see `db/migrations/`).
This script applies migrations to a temporary SQLite database, introspects the schema,
and writes deterministic documentation artifacts.

Artifacts are stored under:
  docs/db/YYYY_MM_DD-HHMMSS-{branch_token}/

Where:
- `branch_token` is the current git branch name, sanitized; detached HEAD becomes
  `detached-<shortsha>`.
- "Latest" is the lexicographically greatest folder name (safe due to timestamp prefix).

Usage (from repo root):
  uv run python scripts/generate_db_schema_docs.py --update
  uv run python scripts/generate_db_schema_docs.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from scripts._schema_utils import _alembic_upgrade_head, _repo_root


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def _git_branch_token(repo_root: Path) -> str:
    try:
        completed = _run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=repo_root,
            check=False,
        )
        branch = completed.stdout.strip()
        if completed.returncode == 0 and branch:
            return _sanitize_branch_token(branch)
    except Exception:
        # Fall back to detached token below.
        pass

    sha = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root).stdout.strip()
    return _sanitize_branch_token(f"detached-{sha}")


_UNSAFE_BRANCH_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_branch_token(raw: str) -> str:
    token = raw.replace("/", "__")
    token = _UNSAFE_BRANCH_CHARS.sub("_", token)
    token = token.strip("_")
    if not token:
        token = "unknown"
    return token[:80]


_VERSION_DIR_RE = re.compile(r"^\d{4}_\d{2}_\d{2}-\d{6}-.+$")


def _latest_version_dir(out_root: Path) -> Path | None:
    if not out_root.exists():
        return None
    candidates: list[Path] = [
        p
        for p in out_root.iterdir()
        if p.is_dir() and _VERSION_DIR_RE.match(p.name) is not None
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


from datetime import datetime, timezone

def _now_version_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y_%m_%d-%H%M%S")


@dataclass(frozen=True)
class _SchemaArtifacts:
    schema_snapshot: dict[str, Any]
    schema_md: str


def _schema_snapshot_from_sqlite(sqlite_path: Path) -> dict[str, Any]:
    engine = sa.create_engine(f"sqlite:///{sqlite_path}")
    inspector = sa.inspect(engine)
    tables = sorted(t for t in inspector.get_table_names() if t != "alembic_version")

    snapshot_tables: dict[str, Any] = {}
    for table_name in tables:
        columns_raw = inspector.get_columns(table_name)
        columns: list[dict[str, Any]] = []
        for col in columns_raw:
            # Keep order stable as returned by SQLite / SQLAlchemy for table columns.
            columns.append(
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": bool(col.get("nullable", True)),
                    "default": col.get("default"),
                    "primary_key": int(col.get("primary_key") or 0),
                }
            )

        pk = inspector.get_pk_constraint(table_name) or {}
        pk_columns = list(pk.get("constrained_columns") or [])
        pk_name = pk.get("name")

        unique_constraints_raw = inspector.get_unique_constraints(table_name) or []
        unique_constraints = [
            {
                "name": uc.get("name"),
                "columns": list(uc.get("column_names") or []),
            }
            for uc in unique_constraints_raw
        ]
        unique_constraints.sort(key=lambda x: (x["name"] or "", x["columns"]))

        indexes_raw = inspector.get_indexes(table_name) or []
        indexes = [
            {
                "name": idx.get("name"),
                "columns": list(idx.get("column_names") or []),
                "unique": bool(idx.get("unique", False)),
            }
            for idx in indexes_raw
        ]
        indexes.sort(key=lambda x: (x["name"] or "", x["columns"], x["unique"]))

        foreign_keys_raw = inspector.get_foreign_keys(table_name) or []
        foreign_keys = []
        for fk in foreign_keys_raw:
            options = fk.get("options") or {}
            foreign_keys.append(
                {
                    "name": fk.get("name"),
                    "columns": list(fk.get("constrained_columns") or []),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": list(fk.get("referred_columns") or []),
                    "ondelete": options.get("ondelete"),
                    "onupdate": options.get("onupdate"),
                }
            )
        foreign_keys.sort(
            key=lambda x: (
                x["referred_table"] or "",
                x["columns"],
                x["referred_columns"],
                x["name"] or "",
            )
        )

        check_constraints_raw = inspector.get_check_constraints(table_name) or []
        check_constraints = [
            {"name": ck.get("name"), "sqltext": ck.get("sqltext")}
            for ck in check_constraints_raw
        ]
        check_constraints.sort(key=lambda x: (x["name"] or "", x["sqltext"] or ""))

        snapshot_tables[table_name] = {
            "columns": columns,
            "primary_key": {"name": pk_name, "columns": pk_columns},
            "foreign_keys": foreign_keys,
            "unique_constraints": unique_constraints,
            "indexes": indexes,
            "check_constraints": check_constraints,
        }

    # Build referenced-by relationships for markdown rendering and helpful diffs.
    referenced_by: dict[str, list[dict[str, Any]]] = {t: [] for t in snapshot_tables}
    for child_table, info in snapshot_tables.items():
        for fk in info["foreign_keys"]:
            parent = fk["referred_table"]
            if parent and parent in referenced_by:
                referenced_by[parent].append(
                    {
                        "from_table": child_table,
                        "from_columns": fk["columns"],
                        "to_columns": fk["referred_columns"],
                        "name": fk["name"],
                    }
                )
    for parent in referenced_by:
        referenced_by[parent].sort(
            key=lambda x: (
                x["from_table"],
                x["from_columns"],
                x["to_columns"],
                x["name"] or "",
            )
        )

    return {
        "dialect": "sqlite",
        "tables": snapshot_tables,
        "referenced_by": referenced_by,
    }


def _render_markdown(snapshot: dict[str, Any], *, mermaid: str) -> str:
    tables: dict[str, Any] = snapshot["tables"]
    referenced_by: dict[str, Any] = snapshot["referenced_by"]

    lines: list[str] = []
    lines.append("# Database schema (Alembic migrations @ head)")
    lines.append("")
    lines.append("## Mermaid Diagram")
    lines.append("")
    lines.append("```mermaid")
    lines.append(mermaid.rstrip())
    lines.append("```")
    lines.append("")
    lines.append(
        "This documentation is generated from a fresh SQLite database after applying "
        "Alembic migrations to `head`."
    )
    lines.append("")

    for table_name in sorted(tables):
        info = tables[table_name]
        lines.append(f"## `{table_name}`")
        lines.append("")

        lines.append(f"### Columns (`{table_name}`)")
        lines.append("")
        lines.append("| name | type | nullable | default | pk |")
        lines.append("| --- | --- | --- | --- | --- |")
        for col in info["columns"]:
            default = col["default"]
            default_str = "" if default is None else str(default)
            pk_pos = col["primary_key"]
            pk_str = "" if not pk_pos else str(pk_pos)
            lines.append(
                f"| `{col['name']}` | `{col['type']}` | "
                f"{'yes' if col['nullable'] else 'no'} | "
                f"`{default_str}` | `{pk_str}` |"
            )
        lines.append("")

        pk = info["primary_key"]
        if pk["columns"]:
            pk_name = pk["name"] or ""
            lines.append(f"### Primary key (`{table_name}`)")
            lines.append("")
            lines.append(f"- Name: `{pk_name}`" if pk_name else "- Name: (none)")
            lines.append("- Columns: " + ", ".join(f"`{c}`" for c in pk["columns"]))
            lines.append("")

        if info["foreign_keys"]:
            lines.append(f"### Foreign keys (`{table_name}`)")
            lines.append("")
            for fk in info["foreign_keys"]:
                name = fk["name"] or "(unnamed)"
                cols = ", ".join(f"`{c}`" for c in fk["columns"])
                ref = f"{fk['referred_table']}({', '.join(fk['referred_columns'])})"
                opts = []
                if fk["ondelete"]:
                    opts.append(f"ondelete={fk['ondelete']}")
                if fk["onupdate"]:
                    opts.append(f"onupdate={fk['onupdate']}")
                opts_str = "" if not opts else f" ({', '.join(opts)})"
                lines.append(f"- `{name}`: {cols} → `{ref}`{opts_str}")
            lines.append("")

        if info["unique_constraints"]:
            lines.append(f"### Unique constraints (`{table_name}`)")
            lines.append("")
            for uc in info["unique_constraints"]:
                name = uc["name"] or "(unnamed)"
                cols = ", ".join(f"`{c}`" for c in uc["columns"])
                lines.append(f"- `{name}`: {cols}")
            lines.append("")

        if info["indexes"]:
            lines.append(f"### Indexes (`{table_name}`)")
            lines.append("")
            for idx in info["indexes"]:
                name = idx["name"] or "(unnamed)"
                cols = ", ".join(f"`{c}`" for c in idx["columns"])
                unique_str = " unique" if idx["unique"] else ""
                lines.append(f"- `{name}`:{unique_str} {cols}")
            lines.append("")

        if info["check_constraints"]:
            lines.append(f"### Check constraints (`{table_name}`)")
            lines.append("")
            for ck in info["check_constraints"]:
                name = ck["name"] or "(unnamed)"
                sqltext = ck["sqltext"] or ""
                lines.append(f"- `{name}`: `{sqltext}`")
            lines.append("")

        if referenced_by.get(table_name):
            lines.append(f"### Referenced by (`{table_name}`)")
            lines.append("")
            for ref in referenced_by[table_name]:
                from_cols = ", ".join(f"`{c}`" for c in ref["from_columns"])
                to_cols = ", ".join(f"`{c}`" for c in ref["to_columns"])
                name = ref["name"] or "(unnamed)"
                lines.append(
                    f"- `{ref['from_table']}` `{name}`: {from_cols} → {to_cols}"
                )
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_mermaid(snapshot: dict[str, Any]) -> str:
    tables: dict[str, Any] = snapshot["tables"]

    fk_columns_by_table: dict[str, set[str]] = {t: set() for t in tables}
    for table_name, info in tables.items():
        for fk in info["foreign_keys"]:
            for c in fk["columns"]:
                fk_columns_by_table[table_name].add(c)

    lines: list[str] = []
    lines.append("erDiagram")

    for table_name in sorted(tables):
        info = tables[table_name]
        lines.append(f"  {table_name} {{")
        for col in info["columns"]:
            col_flags: list[str] = []
            if col["primary_key"]:
                col_flags.append("PK")
            if col["name"] in fk_columns_by_table[table_name]:
                col_flags.append("FK")
            flags_str = "" if not col_flags else " " + " ".join(col_flags)
            lines.append(f"    {col['type']} {col['name']}{flags_str}")
        lines.append("  }")

    # Relationships: parent ||--o{ child
    rels: set[tuple[str, str, str]] = set()
    for child_table, info in tables.items():
        for fk in info["foreign_keys"]:
            parent = fk["referred_table"]
            if not parent:
                continue
            label_name = fk["name"] or "fk"
            label_cols = ", ".join(fk["columns"])
            label = f"{label_name} ({label_cols})" if label_cols else label_name
            rels.add((parent, child_table, label))

    for parent, child, label in sorted(rels):
        lines.append(f'  {parent} ||--o{{ {child} : "{label}"')

    return "\n".join(lines).rstrip() + "\n"


def _artifacts_from_sqlite(sqlite_path: Path) -> _SchemaArtifacts:
    snapshot = _schema_snapshot_from_sqlite(sqlite_path)
    mmd = _render_mermaid(snapshot)
    md = _render_markdown(snapshot, mermaid=mmd)
    return _SchemaArtifacts(schema_snapshot=snapshot, schema_md=md)


def _write_artifacts(out_dir: Path, artifacts: _SchemaArtifacts) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "schema.snapshot.json").write_text(
        json.dumps(artifacts.schema_snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "schema.md").write_text(artifacts.schema_md, encoding="utf-8")


def _diff_summary(a: dict[str, Any], b: dict[str, Any]) -> str:
    a_tables: dict[str, Any] = a.get("tables") or {}
    b_tables: dict[str, Any] = b.get("tables") or {}

    a_names = set(a_tables)
    b_names = set(b_tables)
    added = sorted(b_names - a_names)
    removed = sorted(a_names - b_names)
    common = sorted(a_names & b_names)

    lines: list[str] = []
    if added:
        lines.append("Tables added: " + ", ".join(f"`{t}`" for t in added))
    if removed:
        lines.append("Tables removed: " + ", ".join(f"`{t}`" for t in removed))

    def _col_key(c: dict[str, Any]) -> tuple[Any, ...]:
        return (
            c.get("name"),
            c.get("type"),
            bool(c.get("nullable", True)),
            c.get("default"),
            int(c.get("primary_key") or 0),
        )

    changed_tables: list[str] = []
    for t in common:
        a_cols = {c["name"]: _col_key(c) for c in a_tables[t]["columns"]}
        b_cols = {c["name"]: _col_key(c) for c in b_tables[t]["columns"]}
        if a_cols != b_cols:
            changed_tables.append(t)
            continue
        # FK/unique/index/check changes can be important even if columns match.
        for k in [
            "foreign_keys",
            "unique_constraints",
            "indexes",
            "check_constraints",
            "primary_key",
        ]:
            if a_tables[t].get(k) != b_tables[t].get(k):
                changed_tables.append(t)
                break

    if changed_tables:
        lines.append(
            "Tables changed: " + ", ".join(f"`{t}`" for t in sorted(changed_tables))
        )
    if not lines:
        return "Schema differs (no high-level summary available)."
    return "\n".join(lines)


def _load_snapshot(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise RuntimeError(f"Missing schema snapshot: {path}") from e


def _generate_to_temp(repo_root: Path) -> _SchemaArtifacts:
    with tempfile.TemporaryDirectory(prefix="sim-schema-docs-") as tmpdir:
        sqlite_path = Path(tmpdir) / "schema.sqlite"
        _alembic_upgrade_head(repo_root=repo_root, sqlite_path=sqlite_path)
        return _artifacts_from_sqlite(sqlite_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and/or verify DB schema docs from Alembic migrations."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--update",
        action="store_true",
        help="Write a new versioned schema docs folder under docs/db/.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify the latest docs/db/* folder matches migrations at head.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=None,
        help="Root output directory (default: <repo>/docs/db).",
    )
    parser.add_argument(
        "--keep-temp-db",
        action="store_true",
        help="(Debug) Keep the temporary SQLite DB on disk.",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    out_root: Path = args.out_root or (repo_root / "docs" / "db")

    if args.update:
        branch_token = _git_branch_token(repo_root)
        version_dir_name = f"{_now_version_prefix()}-{branch_token}"
        out_dir = out_root / version_dir_name

        out_root.mkdir(parents=True, exist_ok=True)
        if args.keep_temp_db:
            tmpdir = Path(tempfile.mkdtemp(prefix="sim-schema-docs-"))
            sqlite_path = tmpdir / "schema.sqlite"
            _alembic_upgrade_head(repo_root=repo_root, sqlite_path=sqlite_path)
            artifacts = _artifacts_from_sqlite(sqlite_path)
            _write_artifacts(out_dir, artifacts)
            print(f"Kept temp DB at: {sqlite_path}")
        else:
            with tempfile.TemporaryDirectory(prefix="sim-schema-docs-") as tmpdir:
                sqlite_path = Path(tmpdir) / "schema.sqlite"
                _alembic_upgrade_head(repo_root=repo_root, sqlite_path=sqlite_path)
                artifacts = _artifacts_from_sqlite(sqlite_path)
                _write_artifacts(out_dir, artifacts)

        (out_root / "LATEST.txt").write_text(version_dir_name + "\n", encoding="utf-8")
        print(f"Wrote schema docs to: {out_dir}")
        return 0

    assert args.check
    latest_dir = _latest_version_dir(out_root)
    if latest_dir is None:
        print(
            "ERROR: No baseline schema docs found under docs/db/.\n"
            "Fix: run `uv run python scripts/generate_db_schema_docs.py --update` "
            "and commit the generated folder.\n",
            file=sys.stderr,
        )
        return 1

    baseline_snapshot_path = latest_dir / "schema.snapshot.json"
    baseline_snapshot = _load_snapshot(baseline_snapshot_path)
    if args.keep_temp_db:
        tmpdir = Path(tempfile.mkdtemp(prefix="sim-schema-docs-check-"))
        sqlite_path = tmpdir / "schema.sqlite"
        _alembic_upgrade_head(repo_root=repo_root, sqlite_path=sqlite_path)
        generated_snapshot = _artifacts_from_sqlite(sqlite_path).schema_snapshot
        print(f"Kept temp DB at: {sqlite_path}", file=sys.stderr)
    else:
        generated_artifacts = _generate_to_temp(repo_root)
        generated_snapshot = generated_artifacts.schema_snapshot

    if baseline_snapshot == generated_snapshot:
        return 0

    summary = _diff_summary(baseline_snapshot, generated_snapshot)
    print(
        "ERROR: Database schema docs are out of date (migrations != latest docs).\n\n"
        f"{summary}\n\n"
        f"Baseline folder: {latest_dir}\n"
        f"Baseline files: {latest_dir / 'schema.md'}, {latest_dir / 'schema.snapshot.json'}\n\n"
        "Fix:\n"
        "  uv run python scripts/generate_db_schema_docs.py --update\n\n"
        "After updating, review and commit the new folder under docs/db/, then compare:\n"
        f"  git diff -- {latest_dir} docs/db/<newest-folder>\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
