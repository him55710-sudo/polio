from __future__ import annotations

from pathlib import Path

from unifoli_api.api.routes import diagnosis as diagnosis_route
from unifoli_api.api.routes import render_jobs as render_jobs_route


def _patch_artifact_roots(monkeypatch, tmp_path: Path, route_module) -> Path:
    storage_root = tmp_path / "storage"
    export_root = storage_root / "exports"
    project_root = tmp_path / "project"
    export_root.mkdir(parents=True)
    project_root.mkdir()

    monkeypatch.setattr(route_module, "get_export_root", lambda: export_root)
    monkeypatch.setattr(route_module, "resolve_stored_path", lambda value: storage_root / value)
    monkeypatch.setattr(route_module, "resolve_project_path", lambda value: project_root / value)
    return export_root


def test_diagnosis_report_output_path_accepts_storage_relative_export(monkeypatch, tmp_path: Path) -> None:
    export_root = _patch_artifact_roots(monkeypatch, tmp_path, diagnosis_route)
    report_path = export_root / "diagnosis_reports" / "project-1" / "run-1" / "report.pdf"
    report_path.parent.mkdir(parents=True)
    report_path.write_bytes(b"%PDF-report%")

    resolved = diagnosis_route._resolve_report_output_path(
        "exports/diagnosis_reports/project-1/run-1/report.pdf",
    )

    assert resolved == report_path


def test_render_output_path_accepts_storage_relative_export(monkeypatch, tmp_path: Path) -> None:
    export_root = _patch_artifact_roots(monkeypatch, tmp_path, render_jobs_route)
    output_path = export_root / "rendered" / "job-1" / "report.pdf"
    output_path.parent.mkdir(parents=True)
    output_path.write_bytes(b"%PDF-render%")

    resolved = render_jobs_route._resolve_render_output_path("exports/rendered/job-1/report.pdf")

    assert resolved == output_path
