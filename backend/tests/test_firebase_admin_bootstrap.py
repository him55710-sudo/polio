from __future__ import annotations

from pathlib import Path

from unifoli_api.api.deps import (
    _resolve_firebase_project_id,
    _resolve_google_application_credentials_path,
)
from unifoli_api.core.config import Settings
from unifoli_shared.paths import find_project_root


def test_settings_support_backend_env_file() -> None:
    env_files = tuple(Settings.model_config.get("env_file", ()))
    assert str(find_project_root() / "backend" / ".env") in env_files


def test_resolve_firebase_project_id_prefers_service_account_payload(monkeypatch) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "env-project")

    resolved = _resolve_firebase_project_id({"project_id": "service-account-project"})

    assert resolved == "service-account-project"


def test_resolve_google_application_credentials_path_uses_runtime_resolution(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "./storage/runtime/firebase-service-account.json")

    resolved = _resolve_google_application_credentials_path()

    assert resolved is not None
    assert Path(resolved).name == "firebase-service-account.json"
    assert str(find_project_root()) in resolved
