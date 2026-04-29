"""add guided chat starred fields

Revision ID: 20260426_0020
Revises: 20260417_0019
Create Date: 2026-04-26 04:20:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260426_0020"
down_revision = "20260417_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "starred_keywords_json" not in user_columns:
            op.add_column("users", sa.Column("starred_keywords_json", sa.Text(), nullable=True))

    if "projects" in tables:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "starred_topics_json" not in project_columns:
            op.add_column("projects", sa.Column("starred_topics_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "projects" in tables:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "starred_topics_json" in project_columns:
            op.drop_column("projects", "starred_topics_json")

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "starred_keywords_json" in user_columns:
            op.drop_column("users", "starred_keywords_json")
