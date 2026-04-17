"""add speaker_role to workshop_turns

Revision ID: 20260417_0019
Revises: 20260416_0018
Create Date: 2026-04-17 15:40:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260417_0019"
down_revision = "20260416_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "workshop_turns" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("workshop_turns")}
    if "speaker_role" not in columns:
        op.add_column(
            "workshop_turns",
            sa.Column("speaker_role", sa.String(length=32), nullable=False, server_default="user"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "workshop_turns" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("workshop_turns")}
    if "speaker_role" in columns:
        op.drop_column("workshop_turns", "speaker_role")

