"""add status_message to diagnosis_runs

Revision ID: 20260416_0018
Revises: 20260415_0017
Create Date: 2026-04-16 17:20:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260416_0018"
down_revision = "20260415_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "diagnosis_runs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("diagnosis_runs")}
    if "status_message" not in columns:
        op.add_column("diagnosis_runs", sa.Column("status_message", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "diagnosis_runs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("diagnosis_runs")}
    if "status_message" in columns:
        op.drop_column("diagnosis_runs", "status_message")
