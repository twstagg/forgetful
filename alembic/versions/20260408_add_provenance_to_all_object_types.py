"""add provenance tracking to all object types

Revision ID: 20260408_provenance_all
Revises: 20260321_skills
Create Date: 2026-04-08

Adds provenance tracking fields to all remaining object types:
- projects, documents, code_artifacts, files, skills, entities,
  entity_relationships, plans, tasks

Also adds 3 new provenance fields (agent_id, agent_version, agent_model)
to the memories table which already has the first 6 provenance fields.

Entity relationships get 8 fields (skip confidence — they have their own).
All other tables get 9 fields.

All fields are optional (nullable) for backward compatibility.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.config.settings import settings

# revision identifiers, used by Alembic.
revision: str = "20260408_provenance_all"
down_revision: str | Sequence[str] | None = "20260321_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that get all 9 provenance fields
FULL_PROVENANCE_TABLES = [
    "projects",
    "documents",
    "code_artifacts",
    "files",
    "skills",
    "entities",
    "plans",
    "tasks",
]

# New fields to add to memories (already has the first 6)
NEW_MEMORY_FIELDS = ["agent_id", "agent_version", "agent_model"]


def _add_source_files_column(table_name: str) -> None:
    """Add source_files column with correct type per database."""
    if settings.DATABASE == "Postgres":
        op.add_column(
            table_name,
            sa.Column("source_files", postgresql.ARRAY(sa.String()), nullable=True),
        )
    elif settings.DATABASE == "SQLite":
        op.add_column(
            table_name,
            sa.Column("source_files", sa.JSON(), nullable=True),
        )
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE}")


def _add_full_provenance(table_name: str) -> None:
    """Add all 9 provenance columns to a table."""
    op.add_column(table_name, sa.Column("source_repo", sa.Text(), nullable=True))
    _add_source_files_column(table_name)
    op.add_column(table_name, sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(table_name, sa.Column("encoding_agent", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("encoding_version", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("agent_id", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("agent_version", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("agent_model", sa.Text(), nullable=True))

    # Index on encoding_agent for filtering
    op.create_index(f"ix_{table_name}_encoding_agent", table_name, ["encoding_agent"])


def _drop_full_provenance(table_name: str) -> None:
    """Remove all 9 provenance columns from a table."""
    op.drop_index(f"ix_{table_name}_encoding_agent", table_name=table_name)
    for col in ["source_repo", "source_files", "source_url", "confidence",
                "encoding_agent", "encoding_version", "agent_id", "agent_version", "agent_model"]:
        op.drop_column(table_name, col)


def upgrade() -> None:
    """Add provenance columns to all object type tables."""
    # 1. Add 3 new fields to memories (already has 6 provenance fields)
    for col_name in NEW_MEMORY_FIELDS:
        op.add_column("memories", sa.Column(col_name, sa.Text(), nullable=True))

    # 2. Add full 9-field provenance to all other tables
    for table_name in FULL_PROVENANCE_TABLES:
        _add_full_provenance(table_name)

    # 3. Entity relationships: 8 fields (skip confidence — already has its own)
    op.add_column("entity_relationships", sa.Column("source_repo", sa.Text(), nullable=True))
    _add_source_files_column("entity_relationships")
    op.add_column("entity_relationships", sa.Column("source_url", sa.Text(), nullable=True))
    # confidence intentionally skipped — entity_relationships has its own confidence field
    op.add_column("entity_relationships", sa.Column("encoding_agent", sa.Text(), nullable=True))
    op.add_column("entity_relationships", sa.Column("encoding_version", sa.Text(), nullable=True))
    op.add_column("entity_relationships", sa.Column("agent_id", sa.Text(), nullable=True))
    op.add_column("entity_relationships", sa.Column("agent_version", sa.Text(), nullable=True))
    op.add_column("entity_relationships", sa.Column("agent_model", sa.Text(), nullable=True))
    op.create_index("ix_entity_relationships_encoding_agent", "entity_relationships", ["encoding_agent"])


def downgrade() -> None:
    """Remove provenance columns from all object type tables."""
    # 1. Remove 3 new fields from memories
    for col_name in NEW_MEMORY_FIELDS:
        op.drop_column("memories", col_name)

    # 2. Remove full provenance from all other tables
    for table_name in FULL_PROVENANCE_TABLES:
        _drop_full_provenance(table_name)

    # 3. Remove entity relationship provenance (8 fields)
    op.drop_index("ix_entity_relationships_encoding_agent", table_name="entity_relationships")
    for col in ["source_repo", "source_files", "source_url",
                "encoding_agent", "encoding_version", "agent_id", "agent_version", "agent_model"]:
        op.drop_column("entity_relationships", col)
