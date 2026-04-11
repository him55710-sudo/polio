from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from unifoli_api.api.routes import diagnosis as diagnosis_route


def test_maybe_process_diagnosis_job_inline_processes_queued_job(monkeypatch) -> None:
    called: list[str] = []

    monkeypatch.setattr(
        diagnosis_route,
        "get_settings",
        lambda: SimpleNamespace(allow_inline_job_processing=True),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_job_for_resource",
        lambda db, resource_type, resource_id: SimpleNamespace(id="job-1", status="queued"),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "process_async_job",
        lambda db, job_id: called.append(job_id),
    )

    run = SimpleNamespace(id="run-1", status="PENDING")
    diagnosis_route._maybe_process_diagnosis_job_inline(SimpleNamespace(), run)

    assert called == ["job-1"]


def test_maybe_process_diagnosis_job_inline_skips_terminal_runs(monkeypatch) -> None:
    called: list[str] = []

    monkeypatch.setattr(
        diagnosis_route,
        "get_settings",
        lambda: SimpleNamespace(allow_inline_job_processing=True),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_job_for_resource",
        lambda db, resource_type, resource_id: SimpleNamespace(id="job-2", status="queued"),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "process_async_job",
        lambda db, job_id: called.append(job_id),
    )

    diagnosis_route._maybe_process_diagnosis_job_inline(SimpleNamespace(), SimpleNamespace(id="run-2", status="COMPLETED"))
    diagnosis_route._maybe_process_diagnosis_job_inline(SimpleNamespace(), SimpleNamespace(id="run-3", status="FAILED"))

    assert called == []


def test_maybe_process_report_job_inline_processes_queued_job(monkeypatch) -> None:
    called: list[str] = []

    monkeypatch.setattr(
        diagnosis_route,
        "get_settings",
        lambda: SimpleNamespace(allow_inline_job_processing=True),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_job_for_resource",
        lambda db, resource_type, resource_id: SimpleNamespace(id="report-job-1", status="queued"),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "process_async_job",
        lambda db, job_id: called.append(job_id),
    )

    diagnosis_route._maybe_process_report_job_inline(SimpleNamespace(), SimpleNamespace(id="run-11", status="COMPLETED"))

    assert called == ["report-job-1"]


def test_maybe_process_report_job_inline_skips_non_completed_runs(monkeypatch) -> None:
    called: list[str] = []

    monkeypatch.setattr(
        diagnosis_route,
        "get_settings",
        lambda: SimpleNamespace(allow_inline_job_processing=True),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_job_for_resource",
        lambda db, resource_type, resource_id: SimpleNamespace(id="report-job-2", status="queued"),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "process_async_job",
        lambda db, job_id: called.append(job_id),
    )

    diagnosis_route._maybe_process_report_job_inline(SimpleNamespace(), SimpleNamespace(id="run-12", status="RUNNING"))

    assert called == []


def _minimal_run(*, status: str, result_payload: str | None = None):
    return SimpleNamespace(
        id="run-x",
        project_id="project-x",
        status=status,
        result_payload=result_payload,
        error_message=None,
        review_tasks=[],
        policy_flags=[],
        response_traces=[],
    )


def test_build_run_response_uses_auto_starting_when_report_not_materialized(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )

    def fake_latest_job(db, *, resource_type, resource_id):  # noqa: ANN001, ANN003
        if resource_type == "diagnosis_run":
            return SimpleNamespace(id="diag-job", status="succeeded")
        return None

    monkeypatch.setattr(diagnosis_route, "latest_response_trace", lambda run: None)
    monkeypatch.setattr(diagnosis_route, "get_latest_job_for_resource", fake_latest_job)
    monkeypatch.setattr(diagnosis_route, "get_latest_report_artifact_for_run", lambda db, diagnosis_run_id, report_mode: None)

    response = diagnosis_route._build_run_response(SimpleNamespace(), run)

    assert response.report_status == "AUTO_STARTING"
    assert response.report_async_job_id is None
    assert response.report_artifact_id is None


def test_build_run_response_prefers_failed_report_artifact_error(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )
    failed_artifact = SimpleNamespace(
        id="artifact-1",
        status="FAILED",
        error_message="report render failed",
    )

    def fake_latest_job(db, *, resource_type, resource_id):  # noqa: ANN001, ANN003
        if resource_type == "diagnosis_run":
            return SimpleNamespace(id="diag-job", status="succeeded")
        if resource_type == "diagnosis_report":
            return SimpleNamespace(id="report-job", status="failed", failure_reason="job failed")
        return None

    monkeypatch.setattr(diagnosis_route, "latest_response_trace", lambda run: None)
    monkeypatch.setattr(diagnosis_route, "get_latest_job_for_resource", fake_latest_job)
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_report_artifact_for_run",
        lambda db, diagnosis_run_id, report_mode: failed_artifact,
    )

    response = diagnosis_route._build_run_response(SimpleNamespace(), run)

    assert response.report_status == "FAILED"
    assert response.report_artifact_id == "artifact-1"
    assert response.report_error_message == "report render failed"


def test_ensure_default_report_bootstrap_runs_only_for_completed(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        diagnosis_route,
        "ensure_default_diagnosis_report_job",
        lambda db, **kwargs: calls.append(kwargs["run"].id) or "queued",
    )

    diagnosis_route._ensure_default_report_bootstrap(SimpleNamespace(), _minimal_run(status="RUNNING", result_payload=None))
    diagnosis_route._ensure_default_report_bootstrap(
        SimpleNamespace(),
        _minimal_run(
            status="COMPLETED",
            result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
        ),
    )

    assert calls == ["run-x"]


def test_get_consultant_report_route_processes_queued_auto_report_job(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )
    artifact = SimpleNamespace(id="artifact-1")
    calls: list[str] = []

    monkeypatch.setattr(diagnosis_route, "_get_run_for_user", lambda db, diagnosis_id, user_id: run)
    monkeypatch.setattr(
        diagnosis_route,
        "_ensure_default_report_bootstrap",
        lambda db, current_run: calls.append(f"bootstrap:{current_run.id}"),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "_maybe_process_report_job_inline",
        lambda db, current_run: calls.append(f"process:{current_run.id}"),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_report_artifact_for_run",
        lambda db, diagnosis_run_id, report_mode: artifact,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "build_report_artifact_response",
        lambda **kwargs: {
            "id": kwargs["artifact"].id,
            "include_payload": kwargs["include_payload"],
        },
    )

    response = asyncio.run(
        diagnosis_route.get_consultant_report_route(
            diagnosis_id="run-x",
            artifact_id=None,
            report_mode="premium_10p",
            include_payload=True,
            db=SimpleNamespace(),
            current_user=SimpleNamespace(id="user-1"),
        )
    )

    assert response["id"] == "artifact-1"
    assert calls == ["bootstrap:run-x", "process:run-x"]


def test_get_consultant_report_route_returns_404_when_artifact_missing(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )

    monkeypatch.setattr(diagnosis_route, "_get_run_for_user", lambda db, diagnosis_id, user_id: run)
    monkeypatch.setattr(diagnosis_route, "_ensure_default_report_bootstrap", lambda db, current_run: None)
    monkeypatch.setattr(diagnosis_route, "_maybe_process_report_job_inline", lambda db, current_run: None)
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_report_artifact_for_run",
        lambda db, diagnosis_run_id, report_mode: None,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_project",
        lambda db, project_id, owner_user_id: None,
    )

    try:
        asyncio.run(
            diagnosis_route.get_consultant_report_route(
                diagnosis_id="run-x",
                artifact_id=None,
                report_mode="premium_10p",
                include_payload=True,
                db=SimpleNamespace(),
                current_user=SimpleNamespace(id="user-1"),
            )
        )
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 404


def test_get_consultant_report_route_recovers_stale_artifact_by_regenerating(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )
    recovered_artifact = SimpleNamespace(id="artifact-recovered", status="READY")
    calls: list[str] = []

    async def fake_generate(*args, **kwargs):  # noqa: ANN002, ANN003
        calls.append(kwargs["run"].id)
        return recovered_artifact

    monkeypatch.setattr(diagnosis_route, "_get_run_for_user", lambda db, diagnosis_id, user_id: run)
    monkeypatch.setattr(diagnosis_route, "_ensure_default_report_bootstrap", lambda db, current_run: None)
    monkeypatch.setattr(diagnosis_route, "_maybe_process_report_job_inline", lambda db, current_run: None)
    monkeypatch.setattr(
        diagnosis_route,
        "get_report_artifact_by_id",
        lambda db, diagnosis_run_id, artifact_id: None,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_report_artifact_for_run",
        lambda db, diagnosis_run_id, report_mode: None,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_project",
        lambda db, project_id, owner_user_id: SimpleNamespace(id=project_id),
    )
    monkeypatch.setattr(
        diagnosis_route,
        "generate_consultant_report_artifact",
        fake_generate,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "build_report_artifact_response",
        lambda **kwargs: {"id": kwargs["artifact"].id},
    )

    response = asyncio.run(
        diagnosis_route.get_consultant_report_route(
            diagnosis_id="run-x",
            artifact_id="stale-artifact",
            report_mode="premium_10p",
            include_payload=True,
            db=SimpleNamespace(),
            current_user=SimpleNamespace(id="user-1"),
        )
    )

    assert response["id"] == "artifact-recovered"
    assert calls == ["run-x"]


def test_download_route_does_not_require_project_lookup_for_ready_artifact(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )
    artifact = SimpleNamespace(
        id="artifact-ready",
        status="READY",
        include_appendix=True,
        include_citations=True,
        template_id="consultant_diagnosis_premium_10p",
        version=1,
        generated_file_path=None,
        storage_key="exports/diagnosis_reports/p/r/file.pdf",
    )

    monkeypatch.setattr(diagnosis_route, "_get_run_for_user", lambda db, diagnosis_id, user_id: run)
    monkeypatch.setattr(diagnosis_route, "_ensure_default_report_bootstrap", lambda db, current_run: None)
    monkeypatch.setattr(diagnosis_route, "_maybe_process_report_job_inline", lambda db, current_run: None)
    monkeypatch.setattr(
        diagnosis_route,
        "get_report_artifact_by_id",
        lambda db, diagnosis_run_id, artifact_id: artifact,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_report_artifact_for_run",
        lambda db, diagnosis_run_id, report_mode: artifact,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "report_artifact_storage_key",
        lambda current_artifact: current_artifact.storage_key,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "report_artifact_file_path",
        lambda current_artifact: current_artifact.generated_file_path,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "load_report_artifact_pdf_bytes",
        lambda current_artifact: b"%PDF-test%",
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_project",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("project lookup should not run")),
    )

    response = asyncio.run(
        diagnosis_route.download_consultant_report_pdf_route(
            diagnosis_id="run-x",
            artifact_id="artifact-ready",
            report_mode="premium_10p",
            template_id=None,
            include_appendix=True,
            include_citations=True,
            force_regenerate=False,
            db=SimpleNamespace(),
            current_user=SimpleNamespace(id="user-1"),
        )
    )

    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-test%"


def test_download_route_regenerates_when_ready_artifact_binary_missing(monkeypatch) -> None:
    run = _minimal_run(
        status="COMPLETED",
        result_payload='{"headline":"h","strengths":["s"],"gaps":["g"],"recommended_focus":"f","risk_level":"warning"}',
    )
    stale_artifact = SimpleNamespace(
        id="artifact-stale",
        status="READY",
        include_appendix=True,
        include_citations=True,
        template_id="consultant_diagnosis_premium_10p",
        version=1,
        generated_file_path=None,
        storage_key="exports/diagnosis_reports/p/r/stale.pdf",
    )
    regenerated_artifact = SimpleNamespace(
        id="artifact-regenerated",
        status="READY",
        include_appendix=True,
        include_citations=True,
        template_id="consultant_diagnosis_premium_10p",
        version=2,
        generated_file_path=None,
        storage_key="exports/diagnosis_reports/p/r/regenerated.pdf",
    )
    regen_calls: list[dict[str, object]] = []

    monkeypatch.setattr(diagnosis_route, "_get_run_for_user", lambda db, diagnosis_id, user_id: run)
    monkeypatch.setattr(diagnosis_route, "_ensure_default_report_bootstrap", lambda db, current_run: None)
    monkeypatch.setattr(diagnosis_route, "_maybe_process_report_job_inline", lambda db, current_run: None)
    monkeypatch.setattr(
        diagnosis_route,
        "get_report_artifact_by_id",
        lambda db, diagnosis_run_id, artifact_id: stale_artifact,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_latest_report_artifact_for_run",
        lambda db, diagnosis_run_id, report_mode: stale_artifact,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "report_artifact_storage_key",
        lambda current_artifact: current_artifact.storage_key,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "report_artifact_file_path",
        lambda current_artifact: current_artifact.generated_file_path,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "load_report_artifact_pdf_bytes",
        lambda current_artifact: b"%PDF-regenerated%" if current_artifact.id == "artifact-regenerated" else None,
    )
    monkeypatch.setattr(
        diagnosis_route,
        "get_project",
        lambda db, project_id, owner_user_id: SimpleNamespace(id=project_id),
    )

    async def _fake_generate(*args, **kwargs):  # noqa: ANN002, ANN003
        regen_calls.append(kwargs)
        return regenerated_artifact

    monkeypatch.setattr(diagnosis_route, "generate_consultant_report_artifact", _fake_generate)

    response = asyncio.run(
        diagnosis_route.download_consultant_report_pdf_route(
            diagnosis_id="run-x",
            artifact_id="artifact-stale",
            report_mode="premium_10p",
            template_id=None,
            include_appendix=True,
            include_citations=True,
            force_regenerate=False,
            db=SimpleNamespace(),
            current_user=SimpleNamespace(id="user-1"),
        )
    )

    assert len(regen_calls) == 1
    assert regen_calls[0]["force_regenerate"] is True
    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-regenerated%"

