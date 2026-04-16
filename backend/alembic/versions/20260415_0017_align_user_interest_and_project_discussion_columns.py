"""align user interest and project discussion columns with live ORM models

Revision ID: 20260415_0017
Revises: 20260415_0016
Create Date: 2026-04-15
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260415_0017"
down_revision: Union[str, None] = "20260415_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in _table_names(inspector):
        return
    if column_name in _column_names(inspector, table_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(column)


def _drop_column_if_present(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in _table_names(inspector):
        return
    if column_name not in _column_names(inspector, table_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column(column_name)


def upgrade() -> None:
    _add_column_if_missing(
        "users",
        "interest_universities",
        sa.Column("interest_universities", sa.JSON(), nullable=True, server_default=sa.text("'[]'")),
    )
    _add_column_if_missing(
        "projects",
        "discussion_log",
        sa.Column("discussion_log", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    _drop_column_if_present("projects", "discussion_log")
    _drop_column_if_present("users", "interest_universities")
