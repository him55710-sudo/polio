from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from unifoli_api.core.config import get_settings
from unifoli_api.db.models.parsed_document import ParsedDocument
from unifoli_api.services.document_service import sync_document_async_job_state


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _upgrade_to_head(database_url: str, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        backend_root = _backend_root()
        config = Config(str(backend_root / "alembic.ini"))
        config.set_main_option("script_location", str(backend_root / "alembic"))
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()


def test_alembic_upgrade_adds_marketing_agreed_to_legacy_users_table(tmp_path, monkeypatch) -> None:
    legacy_db_path = tmp_path / "legacy-users.db"
    legacy_engine = create_engine(f"sqlite:///{legacy_db_path.as_posix()}", future=True)

    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    firebase_uid VARCHAR(128) NOT NULL,
                    email VARCHAR(255),
                    name VARCHAR(200),
                    target_university VARCHAR(200),
                    target_major VARCHAR(200),
                    grade VARCHAR(50),
                    track VARCHAR(100),
                    career VARCHAR(200),
                    admission_type VARCHAR(100),
                    interest_universities JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )

    _upgrade_to_head(f"sqlite:///{legacy_db_path.as_posix()}", monkeypatch)

    users_columns = {column["name"] for column in inspect(legacy_engine).get_columns("users")}
    assert "marketing_agreed" in users_columns

    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, firebase_uid, created_at, updated_at)
                VALUES ('legacy-user-1', 'legacy:uid:1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        marketing_agreed = connection.execute(
            text("SELECT marketing_agreed FROM users WHERE id = 'legacy-user-1'")
        ).scalar_one()

    assert marketing_agreed in (0, False)


def test_alembic_head_creates_operational_indexes_and_parsed_document_job_columns(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "fresh-runtime.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    _upgrade_to_head(database_url, monkeypatch)

    runtime_engine = create_engine(database_url, future=True)
    runtime_inspector = inspect(runtime_engine)
    table_names = set(runtime_inspector.get_table_names())

    assert {
        "async_jobs",
        "diagnosis_report_artifacts",
        "llm_cache_entries",
        "payment_orders",
        "research_documents",
        "research_chunks",
    }.issubset(table_names)

    parsed_document_columns = {column["name"] for column in runtime_inspector.get_columns("parsed_documents")}
    diagnosis_run_columns = {column["name"] for column in runtime_inspector.get_columns("diagnosis_runs")}
    assert {
        "latest_async_job_id",
        "latest_async_job_status",
        "latest_async_job_error",
    }.issubset(parsed_document_columns)
    assert "status_message" in diagnosis_run_columns

    user_columns = {column["name"] for column in runtime_inspector.get_columns("users")}
    project_columns = {column["name"] for column in runtime_inspector.get_columns("projects")}
    assert "interest_universities" in user_columns
    assert "discussion_log" in project_columns

    assert "ix_upload_assets_project_created_at" in {
        index["name"] for index in runtime_inspector.get_indexes("upload_assets")
    }
    assert "ix_parsed_documents_project_updated_at" in {
        index["name"] for index in runtime_inspector.get_indexes("parsed_documents")
    }
    assert "ix_async_jobs_resource_created_at" in {
        index["name"] for index in runtime_inspector.get_indexes("async_jobs")
    }
    assert "ix_diagnosis_runs_project_created_at" in {
        index["name"] for index in runtime_inspector.get_indexes("diagnosis_runs")
    }
    assert "ix_diagnosis_report_artifacts_run_mode_version" in {
        index["name"] for index in runtime_inspector.get_indexes("diagnosis_report_artifacts")
    }
    assert "ix_render_jobs_status_created_at" in {
        index["name"] for index in runtime_inspector.get_indexes("render_jobs")
    }


def test_sync_document_async_job_state_keeps_columns_and_metadata_aligned() -> None:
    document = ParsedDocument(
        project_id="project-1",
        upload_asset_id="upload-1",
        parse_metadata={
            "filename": "record.pdf",
            "latest_async_job_id": "stale-job",
            "latest_async_job_status": "failed",
            "latest_async_job_error": "old error",
        },
    )

    sync_document_async_job_state(
        document,
        job_id="job-123",
        job_status="queued",
        job_error=None,
    )

    assert document.latest_async_job_id == "job-123"
    assert document.latest_async_job_status == "queued"
    assert document.latest_async_job_error is None
    assert document.parse_metadata["latest_async_job_id"] == "job-123"
    assert document.parse_metadata["latest_async_job_status"] == "queued"
    assert "latest_async_job_error" not in document.parse_metadata
