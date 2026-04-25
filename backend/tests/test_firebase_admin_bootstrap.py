from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from unifoli_api.api.deps import (
    _load_firebase_service_account_payload,
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


def test_resolve_firebase_project_id_falls_back_to_settings_when_env_is_not_exported(monkeypatch) -> None:
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.setattr(
        "unifoli_api.api.deps._get_auth_bootstrap_settings",
        lambda: SimpleNamespace(firebase_project_id="settings-project-id"),
    )

    resolved = _resolve_firebase_project_id()

    assert resolved == "settings-project-id"


def test_resolve_google_application_credentials_path_falls_back_to_settings_when_env_is_not_exported(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(
        "unifoli_api.api.deps._get_auth_bootstrap_settings",
        lambda: SimpleNamespace(google_application_credentials="./storage/runtime/firebase-service-account.json"),
    )

    resolved = _resolve_google_application_credentials_path()

    assert resolved is not None
    assert Path(resolved).name == "firebase-service-account.json"
    assert str(find_project_root()) in resolved


def test_load_firebase_service_account_payload_accepts_vercel_quoted_pretty_json() -> None:
    raw = (
        '"{\\n  "type": "service_account",\\n  "project_id": "demo-project",\\n'
        '  "private_key": "-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----\\n",\\n'
        '  "client_email": "firebase-adminsdk@example.iam.gserviceaccount.com"\\n}\\n"'
    )

    payload = _load_firebase_service_account_payload(raw)

    assert payload["type"] == "service_account"
    assert payload["project_id"] == "demo-project"
    assert "\\n" not in payload["private_key"]
    assert "\n" in payload["private_key"]


def test_load_firebase_service_account_payload_accepts_json_string_payload() -> None:
    raw = (
        '"{\\"type\\":\\"service_account\\",\\"project_id\\":\\"demo-project\\",'
        '\\"private_key\\":\\"-----BEGIN PRIVATE KEY-----\\\\nabc\\\\n-----END PRIVATE KEY-----\\\\n\\",'
        '\\"client_email\\":\\"firebase-adminsdk@example.iam.gserviceaccount.com\\"}"'
    )

    payload = _load_firebase_service_account_payload(raw)

    assert payload["project_id"] == "demo-project"
    assert "\n" in payload["private_key"]
