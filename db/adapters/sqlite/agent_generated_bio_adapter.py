"""SQLite adapter for agent generated bios."""

import json
import sqlite3
from typing import Iterable

from db.adapters.base import AgentGeneratedBioDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import agent_generated_bios
from simulation.core.models.agent_generated_bio import AgentGeneratedBio
from simulation.core.models.generated.base import GenerationMetadata

AGENT_GENERATED_BIO_COLUMNS = ordered_column_names(agent_generated_bios)
AGENT_GENERATED_BIO_REQUIRED_FIELDS = required_column_names(agent_generated_bios)
_INSERT_AGENT_GENERATED_BIO_SQL = (
    f"INSERT INTO agent_generated_bios ({', '.join(AGENT_GENERATED_BIO_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_GENERATED_BIO_COLUMNS)})"
)


class SQLiteAgentGeneratedBioAdapter(AgentGeneratedBioDatabaseAdapter):
    """SQLite implementation for agent generated bios."""

    def _validate_row(self, row: sqlite3.Row, context: str | None = None) -> None:
        validate_required_fields(
            row, AGENT_GENERATED_BIO_REQUIRED_FIELDS, context=context
        )

    def _row_to_model(self, row: sqlite3.Row) -> AgentGeneratedBio:
        metadata_json = row["generation_metadata_json"]
        generation_metadata: dict | None = None
        if metadata_json:
            generation_metadata = json.loads(metadata_json)
        return AgentGeneratedBio(
            id=row["id"],
            agent_id=row["agent_id"],
            generated_bio=row["generated_bio"],
            metadata=GenerationMetadata(
                model_used=row["model_used"],
                generation_metadata=generation_metadata,
                created_at=row["created_at"],
            ),
        )

    def write_agent_generated_bio(
        self, bio: AgentGeneratedBio, *, conn: sqlite3.Connection
    ) -> None:
        metadata_json: str | None = (
            json.dumps(bio.metadata.generation_metadata)
            if bio.metadata.generation_metadata is not None
            else None
        )
        value_map = {
            "id": bio.id,
            "agent_id": bio.agent_id,
            "generated_bio": bio.generated_bio,
            "model_used": bio.metadata.model_used,
            "generation_metadata_json": metadata_json,
            "created_at": bio.metadata.created_at,
        }
        row_values = tuple(value_map[col] for col in AGENT_GENERATED_BIO_COLUMNS)
        conn.execute(_INSERT_AGENT_GENERATED_BIO_SQL, row_values)

    def read_latest_agent_generated_bio(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> AgentGeneratedBio | None:
        row = conn.execute(
            "SELECT * FROM agent_generated_bios WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        self._validate_row(row, context=f"agent_id={agent_id}")
        return self._row_to_model(row)

    def list_agent_generated_bios(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> list[AgentGeneratedBio]:
        rows = conn.execute(
            "SELECT * FROM agent_generated_bios WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
        result: list[AgentGeneratedBio] = []
        for row in rows:
            self._validate_row(row, context=f"agent_id={agent_id}")
            result.append(self._row_to_model(row))
        return result

    def read_latest_agent_generated_bios_by_agent_ids(
        self, agent_ids: Iterable[str], *, conn: sqlite3.Connection
    ) -> dict[str, AgentGeneratedBio | None]:
        agent_ids_list = list(agent_ids)
        if not agent_ids_list:
            return {}
        q_marks = ", ".join("?" for _ in agent_ids_list)
        rows = conn.execute(
            "SELECT * FROM agent_generated_bios "
            f"WHERE agent_id IN ({q_marks}) ORDER BY agent_id, created_at DESC",
            tuple(agent_ids_list),
        ).fetchall()
        result: dict[str, AgentGeneratedBio | None] = {}
        for row in rows:
            aid = row["agent_id"]
            if aid not in result:
                self._validate_row(row, context=f"agent_id={aid}")
                result[aid] = self._row_to_model(row)
        for aid in agent_ids_list:
            result.setdefault(aid, None)
        return result
