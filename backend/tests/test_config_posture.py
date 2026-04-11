from __future__ import annotations

import pytest

from unifoli_api.core.config import Settings


def test_serverless_runtime_blocks_sqlite_without_escape_hatch(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")

    with pytest.raises(ValueError, match="SQLite runtime database is blocked"):
        Settings(
            app_env="production",
            app_debug=False,
            auth_allow_local_dev_bypass=False,
            llm_provider="gemini",
            database_url="sqlite:///./storage/runtime/unifoli.db?check_same_thread=False&timeout=30",
        )


def test_serverless_runtime_allows_sqlite_with_explicit_escape_hatch(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")

    settings = Settings(
        app_env="production",
        app_debug=False,
        auth_allow_local_dev_bypass=False,
        llm_provider="gemini",
        allow_production_sqlite=True,
        database_url="sqlite:///./storage/runtime/unifoli.db?check_same_thread=False&timeout=30",
    )

    assert settings.allow_production_sqlite is True


def test_serverless_runtime_does_not_crash_on_local_ollama_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")

    settings = Settings(
        app_env="production",
        app_debug=False,
        auth_allow_local_dev_bypass=False,
        llm_provider="ollama",
        ollama_base_url="http://localhost:11434/v1",
        allow_production_sqlite=True,
        database_url="sqlite:///./storage/runtime/unifoli.db?check_same_thread=False&timeout=30",
    )

    assert settings.llm_provider == "ollama"

