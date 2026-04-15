"""harden operational indexes and align runtime tables with the live models

Revision ID: 20260415_0016
Revises: 20260409_0015
Create Date: 2026-04-15
"""
from __future__ import annotations

import json
from typing import Any, Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20260415_0016"
down_revision: Union[str, None] = "20260409_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_index_if_missing(inspector, table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if table_name not in _table_names(inspector):
        return
    if index_name in _index_names(inspector, table_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_present(inspector, table_name: str, index_name: str) -> None:
    if table_name not in _table_names(inspector):
        return
    if index_name not in _index_names(inspector, table_name):
        return
    op.drop_index(index_name, table_name=table_name)


def _decode_metadata(raw_value: Any) -> dict[str, Any]:
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            decoded = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _create_missing_runtime_tables(bind) -> None:
    inspector = inspect(bind)
    tables = _table_names(inspector)
    embedding_type = Vector(1536) if bind.dialect.name == "postgresql" else sa.Text()

    if "async_jobs" not in tables:
        op.create_table(
            "async_jobs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=True),
            sa.Column("job_type", sa.String(length=64), nullable=False),
            sa.Column("resource_type", sa.String(length=64), nullable=False),
            sa.Column("resource_id", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("failure_history", sa.JSON(), nullable=False),
            sa.Column("progress_stage", sa.String(length=64), nullable=True),
            sa.Column("progress_message", sa.Text(), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_async_jobs_project_id", "async_jobs", ["project_id"], unique=False)
        op.create_index("ix_async_jobs_job_type", "async_jobs", ["job_type"], unique=False)
        op.create_index("ix_async_jobs_resource_type", "async_jobs", ["resource_type"], unique=False)
        op.create_index("ix_async_jobs_resource_id", "async_jobs", ["resource_id"], unique=False)
        op.create_index("ix_async_jobs_status", "async_jobs", ["status"], unique=False)
        op.create_index("ix_async_jobs_next_attempt_at", "async_jobs", ["next_attempt_at"], unique=False)

    if "diagnosis_report_artifacts" not in tables:
        op.create_table(
            "diagnosis_report_artifacts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("diagnosis_run_id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("report_mode", sa.String(length=32), nullable=False, server_default="premium_10p"),
            sa.Column("template_id", sa.String(length=80), nullable=True),
            sa.Column("export_format", sa.String(length=16), nullable=False, server_default="pdf"),
            sa.Column("include_appendix", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("include_citations", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="READY"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("report_payload_json", sa.Text(), nullable=False),
            sa.Column("storage_provider", sa.String(length=32), nullable=True),
            sa.Column("storage_key", sa.Text(), nullable=True),
            sa.Column("generated_file_path", sa.Text(), nullable=True),
            sa.Column("execution_metadata_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["diagnosis_run_id"], ["diagnosis_runs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_diagnosis_report_artifacts_diagnosis_run_id",
            "diagnosis_report_artifacts",
            ["diagnosis_run_id"],
            unique=False,
        )
        op.create_index(
            "ix_diagnosis_report_artifacts_project_id",
            "diagnosis_report_artifacts",
            ["project_id"],
            unique=False,
        )

    if "llm_cache_entries" not in tables:
        op.create_table(
            "llm_cache_entries",
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("scope_key", sa.String(length=255), nullable=False),
            sa.Column("feature_name", sa.String(length=120), nullable=False),
            sa.Column("model_name", sa.String(length=120), nullable=False),
            sa.Column("config_version", sa.String(length=64), nullable=False),
            sa.Column("response_format", sa.String(length=16), nullable=False, server_default="json"),
            sa.Column("response_payload", sa.Text(), nullable=False),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("key"),
        )
        op.create_index("ix_llm_cache_entries_scope_key", "llm_cache_entries", ["scope_key"], unique=False)
        op.create_index("ix_llm_cache_entries_feature_name", "llm_cache_entries", ["feature_name"], unique=False)
        op.create_index("ix_llm_cache_entries_expires_at", "llm_cache_entries", ["expires_at"], unique=False)

    if "payment_orders" not in tables:
        op.create_table(
            "payment_orders",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=24), nullable=False, server_default="toss"),
            sa.Column("plan_code", sa.String(length=32), nullable=False),
            sa.Column("order_id", sa.String(length=128), nullable=False),
            sa.Column("order_name", sa.String(length=200), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
            sa.Column("payment_key", sa.String(length=200), nullable=True),
            sa.Column("method", sa.String(length=80), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failure_code", sa.String(length=120), nullable=True),
            sa.Column("failure_message", sa.Text(), nullable=True),
            sa.Column("checkout_request", sa.JSON(), nullable=True),
            sa.Column("confirm_response", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_payment_orders_user_id", "payment_orders", ["user_id"], unique=False)
        op.create_index("ix_payment_orders_order_id", "payment_orders", ["order_id"], unique=True)

    if "research_documents" not in tables:
        op.create_table(
            "research_documents",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("provenance_type", sa.String(length=32), nullable=False, server_default="EXTERNAL_RESEARCH"),
            sa.Column("source_type", sa.String(length=32), nullable=False),
            sa.Column("source_classification", sa.String(length=32), nullable=False, server_default="EXPERT_COMMENTARY"),
            sa.Column("trust_rank", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("canonical_url", sa.String(length=1000), nullable=True),
            sa.Column("external_id", sa.String(length=255), nullable=True),
            sa.Column("publisher", sa.String(length=255), nullable=True),
            sa.Column("published_on", sa.Date(), nullable=True),
            sa.Column("usage_note", sa.Text(), nullable=True),
            sa.Column("copyright_note", sa.Text(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("parser_name", sa.String(length=80), nullable=False, server_default="research_pipeline"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("content_markdown", sa.Text(), nullable=False, server_default=""),
            sa.Column("author_names", sa.JSON(), nullable=False),
            sa.Column("source_metadata", sa.JSON(), nullable=False),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_research_documents_project_id", "research_documents", ["project_id"], unique=False)
        op.create_index("ix_research_documents_source_type", "research_documents", ["source_type"], unique=False)
        op.create_index(
            "ix_research_documents_source_classification",
            "research_documents",
            ["source_classification"],
            unique=False,
        )
        op.create_index("ix_research_documents_trust_rank", "research_documents", ["trust_rank"], unique=False)
        op.create_index("ix_research_documents_content_hash", "research_documents", ["content_hash"], unique=False)
        op.create_index("ix_research_documents_status", "research_documents", ["status"], unique=False)

    if "research_chunks" not in tables:
        op.create_table(
            "research_chunks",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("provenance_type", sa.String(length=32), nullable=False, server_default="EXTERNAL_RESEARCH"),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("char_start", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("char_end", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content_text", sa.Text(), nullable=False),
            sa.Column("embedding_model", sa.String(length=120), nullable=True),
            sa.Column("embedding", embedding_type, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["research_documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("document_id", "chunk_index", name="uq_research_chunk_index"),
        )
        op.create_index("ix_research_chunks_document_id", "research_chunks", ["document_id"], unique=False)
        op.create_index("ix_research_chunks_project_id", "research_chunks", ["project_id"], unique=False)


def _backfill_parsed_document_job_state(bind) -> None:
    inspector = inspect(bind)
    tables = _table_names(inspector)
    if "parsed_documents" not in tables:
        return

    parsed_documents = sa.table(
        "parsed_documents",
        sa.column("id", sa.String(length=36)),
        sa.column("parse_metadata", sa.JSON()),
        sa.column("latest_async_job_id", sa.String(length=36)),
        sa.column("latest_async_job_status", sa.String(length=32)),
        sa.column("latest_async_job_error", sa.Text()),
    )
    async_jobs = sa.table(
        "async_jobs",
        sa.column("id", sa.String(length=36)),
        sa.column("resource_type", sa.String(length=64)),
        sa.column("resource_id", sa.String(length=64)),
        sa.column("status", sa.String(length=32)),
        sa.column("failure_reason", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    rows = bind.execute(
        sa.select(
            parsed_documents.c.id,
            parsed_documents.c.parse_metadata,
            parsed_documents.c.latest_async_job_id,
            parsed_documents.c.latest_async_job_status,
            parsed_documents.c.latest_async_job_error,
        )
    ).mappings()

    has_async_jobs = "async_jobs" in tables
    for row in rows:
        metadata = _decode_metadata(row["parse_metadata"])
        latest_job = None
        if has_async_jobs:
            latest_job = bind.execute(
                sa.select(
                    async_jobs.c.id,
                    async_jobs.c.status,
                    async_jobs.c.failure_reason,
                )
                .where(
                    async_jobs.c.resource_type == "parsed_document",
                    async_jobs.c.resource_id == row["id"],
                )
                .order_by(async_jobs.c.created_at.desc(), async_jobs.c.id.desc())
                .limit(1)
            ).mappings().first()

        values: dict[str, Any] = {}
        if not _normalized_text(row["latest_async_job_id"]):
            values["latest_async_job_id"] = _normalized_text(
                (latest_job or {}).get("id") if latest_job else metadata.get("latest_async_job_id")
            )
        if not _normalized_text(row["latest_async_job_status"]):
            values["latest_async_job_status"] = _normalized_text(
                (latest_job or {}).get("status") if latest_job else metadata.get("latest_async_job_status")
            )
        if not _normalized_text(row["latest_async_job_error"]):
            values["latest_async_job_error"] = _normalized_text(
                (latest_job or {}).get("failure_reason") if latest_job else metadata.get("latest_async_job_error")
            )

        sanitized_values = {key: value for key, value in values.items() if value is not None}
        if not sanitized_values:
            continue

        bind.execute(
            parsed_documents.update()
            .where(parsed_documents.c.id == row["id"])
            .values(**sanitized_values)
        )


def upgrade() -> None:
    bind = op.get_bind()
    _create_missing_runtime_tables(bind)

    inspector = inspect(bind)
    tables = _table_names(inspector)

    if "parsed_documents" in tables:
        columns = _column_names(inspector, "parsed_documents")
        if "latest_async_job_id" not in columns:
            op.add_column("parsed_documents", sa.Column("latest_async_job_id", sa.String(length=36), nullable=True))
        if "latest_async_job_status" not in columns:
            op.add_column("parsed_documents", sa.Column("latest_async_job_status", sa.String(length=32), nullable=True))
        if "latest_async_job_error" not in columns:
            op.add_column("parsed_documents", sa.Column("latest_async_job_error", sa.Text(), nullable=True))
        _backfill_parsed_document_job_state(bind)

    inspector = inspect(bind)
    _create_index_if_missing(
        inspector,
        "upload_assets",
        "ix_upload_assets_project_created_at",
        ["project_id", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "parsed_documents",
        "ix_parsed_documents_project_updated_at",
        ["project_id", "updated_at"],
    )
    _create_index_if_missing(
        inspector,
        "parsed_documents",
        "ix_parsed_documents_status_updated_at",
        ["status", "updated_at"],
    )
    _create_index_if_missing(
        inspector,
        "async_jobs",
        "ix_async_jobs_resource_created_at",
        ["resource_type", "resource_id", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "async_jobs",
        "ix_async_jobs_status_next_attempt_at",
        ["status", "next_attempt_at", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "async_jobs",
        "ix_async_jobs_project_created_at",
        ["project_id", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "diagnosis_runs",
        "ix_diagnosis_runs_project_created_at",
        ["project_id", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "diagnosis_runs",
        "ix_diagnosis_runs_status_created_at",
        ["status", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "diagnosis_report_artifacts",
        "ix_diagnosis_report_artifacts_run_mode_version",
        ["diagnosis_run_id", "report_mode", "version", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "diagnosis_report_artifacts",
        "ix_diagnosis_report_artifacts_project_created_at",
        ["project_id", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "render_jobs",
        "ix_render_jobs_draft_id",
        ["draft_id"],
    )
    _create_index_if_missing(
        inspector,
        "render_jobs",
        "ix_render_jobs_project_created_at",
        ["project_id", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "render_jobs",
        "ix_render_jobs_status_created_at",
        ["status", "created_at"],
    )
    _create_index_if_missing(
        inspector,
        "projects",
        "ix_projects_owner_updated_at",
        ["owner_user_id", "updated_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _drop_index_if_present(inspector, "projects", "ix_projects_owner_updated_at")
    _drop_index_if_present(inspector, "render_jobs", "ix_render_jobs_status_created_at")
    _drop_index_if_present(inspector, "render_jobs", "ix_render_jobs_project_created_at")
    _drop_index_if_present(inspector, "render_jobs", "ix_render_jobs_draft_id")
    _drop_index_if_present(
        inspector,
        "diagnosis_report_artifacts",
        "ix_diagnosis_report_artifacts_project_created_at",
    )
    _drop_index_if_present(
        inspector,
        "diagnosis_report_artifacts",
        "ix_diagnosis_report_artifacts_run_mode_version",
    )
    _drop_index_if_present(inspector, "diagnosis_runs", "ix_diagnosis_runs_status_created_at")
    _drop_index_if_present(inspector, "diagnosis_runs", "ix_diagnosis_runs_project_created_at")
    _drop_index_if_present(inspector, "async_jobs", "ix_async_jobs_project_created_at")
    _drop_index_if_present(inspector, "async_jobs", "ix_async_jobs_status_next_attempt_at")
    _drop_index_if_present(inspector, "async_jobs", "ix_async_jobs_resource_created_at")
    _drop_index_if_present(inspector, "parsed_documents", "ix_parsed_documents_status_updated_at")
    _drop_index_if_present(inspector, "parsed_documents", "ix_parsed_documents_project_updated_at")
    _drop_index_if_present(inspector, "upload_assets", "ix_upload_assets_project_created_at")

    inspector = inspect(bind)
    if "parsed_documents" in _table_names(inspector):
        columns = _column_names(inspector, "parsed_documents")
        if "latest_async_job_error" in columns:
            op.drop_column("parsed_documents", "latest_async_job_error")
        if "latest_async_job_status" in columns:
            op.drop_column("parsed_documents", "latest_async_job_status")
        if "latest_async_job_id" in columns:
            op.drop_column("parsed_documents", "latest_async_job_id")
