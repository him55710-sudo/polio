"""add durable storage fields to diagnosis_report_artifacts

Revision ID: 20260409_0015
Revises: 20260408_0014
Create Date: 2026-04-09
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20260409_0015"
down_revision: Union[str, None] = "20260408_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "diagnosis_report_artifacts" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("diagnosis_report_artifacts")}
    if "storage_provider" not in columns:
        op.add_column("diagnosis_report_artifacts", sa.Column("storage_provider", sa.String(length=32), nullable=True))
    if "storage_key" not in columns:
        op.add_column("diagnosis_report_artifacts", sa.Column("storage_key", sa.Text(), nullable=True))
    if "execution_metadata_json" not in columns:
        op.add_column("diagnosis_report_artifacts", sa.Column("execution_metadata_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "diagnosis_report_artifacts" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("diagnosis_report_artifacts")}
    if "execution_metadata_json" in columns:
        op.drop_column("diagnosis_report_artifacts", "execution_metadata_json")
    if "storage_key" in columns:
        op.drop_column("diagnosis_report_artifacts", "storage_key")
    if "storage_provider" in columns:
        op.drop_column("diagnosis_report_artifacts", "storage_provider")
