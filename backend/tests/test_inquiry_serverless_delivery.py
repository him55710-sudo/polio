from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from unifoli_api.core.config import get_settings
from unifoli_api.core.database import SessionLocal
from unifoli_api.db.models.inquiry import Inquiry
from unifoli_api.main import app
from unifoli_api.services import inquiry_service


def test_public_inquiry_submission_processes_email_inline_when_serverless(monkeypatch) -> None:
    settings = get_settings()
    originals = {
        "allow_inline_job_processing": settings.allow_inline_job_processing,
        "async_jobs_inline_dispatch": settings.async_jobs_inline_dispatch,
        "serverless_runtime": settings.serverless_runtime,
        "smtp_enabled": settings.smtp_enabled,
        "smtp_server": settings.smtp_server,
        "smtp_port": settings.smtp_port,
        "smtp_username": settings.smtp_username,
        "smtp_password": settings.smtp_password,
        "smtp_receiver_email": settings.smtp_receiver_email,
    }
    for key, value in {
        "allow_inline_job_processing": True,
        "async_jobs_inline_dispatch": True,
        "serverless_runtime": True,
        "smtp_enabled": True,
        "smtp_server": "smtp.naver.com",
        "smtp_port": 587,
        "smtp_username": "sender@naver.com",
        "smtp_password": "app-password",
        "smtp_receiver_email": "mongben@naver.com",
    }.items():
        setattr(settings, key, value)

    delivered = {"count": 0}

    def fake_send_via_smtp(**kwargs) -> None:  # noqa: ANN003
        delivered["count"] += 1

    monkeypatch.setattr(inquiry_service, "_send_via_smtp", fake_send_via_smtp)

    payload = {
        "inquiry_type": "one_to_one",
        "name": "Tester",
        "email": "tester@example.com",
        "subject": "Login question",
        "message": "I cannot submit my inquiry unless the mail delivery works correctly.",
        "inquiry_category": "account_login",
        "source_path": "/contact?type=support",
    }

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/inquiries", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "delivery_sent"
        assert body["delivery_status"] == "sent"
        assert body["delivery_retry_needed"] is False
        assert delivered["count"] == 1

        with SessionLocal() as db:
            inquiry = db.scalar(select(Inquiry).where(Inquiry.id == body["id"]))
            assert inquiry is not None
            assert inquiry.status == "delivery_sent"
            assert inquiry.extra_fields["delivery"]["status"] == "sent"
            assert inquiry.extra_fields["delivery"]["attempt_count"] == 1
    finally:
        for key, value in originals.items():
            setattr(settings, key, value)
