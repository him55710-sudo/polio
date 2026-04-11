from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from unifoli_api.core.config import get_settings
from unifoli_api.db.models.draft import Draft
from unifoli_api.db.models.project import Project
from unifoli_api.db.models.render_job import RenderJob
from unifoli_api.schemas.render_job import (
    RenderFormatInfo,
    RenderJobCreate,
    RenderTemplateInfo,
    RenderTemplatePreviewInfo,
)
from unifoli_api.services.project_service import list_project_discussion_log
from unifoli_domain.enums import AsyncJobType, RenderFormat, RenderStatus
from unifoli_render.dispatcher import dispatch_render
from unifoli_render.models import RenderBuildContext
from unifoli_render.template_registry import (
    RenderExportPolicy,
    RenderTemplate,
    get_default_template_id,
    get_template,
    list_templates,
)
from unifoli_shared.paths import to_stored_path
from unifoli_shared.storage import get_storage_provider

logger = logging.getLogger("unifoli.api.render_jobs")


def _serialize_template(template: RenderTemplate) -> RenderTemplateInfo:
    return RenderTemplateInfo(
        id=template.id,
        label=template.label,
        description=template.description,
        supported_formats=list(template.supported_formats),
        category=template.category,
        section_schema=list(template.section_schema),
        density=template.density,
        visual_priority=template.visual_priority,
        supports_provenance_appendix=template.supports_provenance_appendix,
        recommended_for=list(template.recommended_for),
        preview=RenderTemplatePreviewInfo(
            accent_color=template.preview.accent_color,
            surface_tone=template.preview.surface_tone,
            cover_title=template.preview.cover_title,
            preview_sections=list(template.preview.preview_sections),
            thumbnail_hint=template.preview.thumbnail_hint,
        ),
    )


def get_render_format_catalog() -> list[RenderFormatInfo]:
    return [
        RenderFormatInfo(
            format=RenderFormat.PDF,
            implementation_level="reportlab",
            description="Creates a template-driven PDF export with grounded section styling.",
            default_template_id=get_default_template_id(RenderFormat.PDF),
        ),
        RenderFormatInfo(
            format=RenderFormat.PPTX,
            implementation_level="python-pptx",
            description="Creates a template-driven presentation with section-based slides.",
            default_template_id=get_default_template_id(RenderFormat.PPTX),
        ),
        RenderFormatInfo(
            format=RenderFormat.HWPX,
            implementation_level="template",
            description="Creates a conservative HWPX package for school-friendly submission.",
            default_template_id=get_default_template_id(RenderFormat.HWPX),
        ),
    ]


def get_render_template_catalog(render_format: RenderFormat | None = None) -> list[RenderTemplateInfo]:
    return [_serialize_template(template) for template in list_templates(render_format=render_format)]


def _resolve_selected_template(*, render_format: RenderFormat, template_id: str | None) -> RenderTemplate:
    return get_template(template_id, render_format=render_format)


def create_render_job(db: Session, payload: RenderJobCreate) -> RenderJob | None:
    project = db.get(Project, payload.project_id)
    draft = db.get(Draft, payload.draft_id)

    if not project or not draft or draft.project_id != project.id:
        return None

    template = _resolve_selected_template(
        render_format=payload.render_format,
        template_id=payload.template_id,
    )

    job = RenderJob(
        project_id=payload.project_id,
        draft_id=payload.draft_id,
        render_format=payload.render_format.value,
        template_id=template.id,
        include_provenance_appendix=payload.include_provenance_appendix,
        hide_internal_provenance_on_final_export=payload.hide_internal_provenance_on_final_export,
        requested_by=payload.requested_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from unifoli_api.services.async_job_service import create_async_job

    create_async_job(
        db,
        job_type=AsyncJobType.RENDER.value,
        resource_type="render_job",
        resource_id=job.id,
        project_id=job.project_id,
        payload={"render_job_id": job.id},
    )
    return job


def list_render_jobs_for_owner(db: Session, owner_user_id: str) -> list[RenderJob]:
    stmt = (
        select(RenderJob)
        .join(Project, Project.id == RenderJob.project_id)
        .where(Project.owner_user_id == owner_user_id)
        .order_by(RenderJob.created_at.desc())
    )
    return list(db.scalars(stmt))


def get_render_job(db: Session, job_id: str) -> RenderJob | None:
    return db.get(RenderJob, job_id)


def get_render_job_for_owner(db: Session, job_id: str, owner_user_id: str) -> RenderJob | None:
    stmt = (
        select(RenderJob)
        .join(Project, Project.id == RenderJob.project_id)
        .where(RenderJob.id == job_id, Project.owner_user_id == owner_user_id)
    )
    return db.scalar(stmt)


def get_next_queued_render_job(db: Session) -> RenderJob | None:
    stmt = (
        select(RenderJob)
        .where(RenderJob.status == RenderStatus.QUEUED.value)
        .order_by(RenderJob.created_at.asc())
    )
    return db.scalars(stmt).first()


def load_render_support_payload(db: Session, project_id: str) -> dict[str, object]:
    from unifoli_api.db.models.workshop import DraftArtifact, WorkshopSession

    stmt = (
        select(DraftArtifact)
        .join(WorkshopSession, WorkshopSession.id == DraftArtifact.session_id)
        .where(WorkshopSession.project_id == project_id)
        .order_by(DraftArtifact.created_at.desc())
    )
    artifact = db.scalars(stmt).first()
    if artifact is None:
        return {
            "visual_specs": [],
            "math_expressions": [],
            "evidence_map": {},
        }

    return {
        "visual_specs": [
            item for item in (artifact.visual_specs or []) if item.get("approval_status") == "approved"
        ],
        "math_expressions": [
            item for item in (artifact.math_expressions or []) if item.get("approval_status") == "approved"
        ],
        "evidence_map": dict(artifact.evidence_map or {}),
    }


def process_render_job(db: Session, job_id: str) -> RenderJob | None:
    job = db.get(RenderJob, job_id)
    if not job:
        return None

    job.status = RenderStatus.PROCESSING.value
    db.commit()
    db.refresh(job)

    try:
        draft = db.get(Draft, job.draft_id)
        project = db.get(Project, job.project_id)
        if not draft or not project:
            raise ValueError("Project or draft missing while processing render job.")

        template = _resolve_selected_template(
            render_format=RenderFormat(job.render_format),
            template_id=job.template_id,
        )
        support_payload = load_render_support_payload(db, project.id)
        context = RenderBuildContext(
            project_id=project.id,
            project_title=project.title,
            draft_id=draft.id,
            draft_title=draft.title,
            render_format=RenderFormat(job.render_format),
            content_markdown=draft.content_markdown,
            requested_by=job.requested_by,
            job_id=job.id,
            visual_specs=list(support_payload["visual_specs"]),
            math_expressions=list(support_payload["math_expressions"]),
            evidence_map=dict(support_payload["evidence_map"]),
            authenticity_log_lines=list_project_discussion_log(project),
            template_id=template.id,
            export_policy=RenderExportPolicy(
                include_provenance_appendix=job.include_provenance_appendix,
                hide_internal_provenance_on_final_export=job.hide_internal_provenance_on_final_export,
            ),
        )
        # Generate output path
        ext = job.render_format.lower()
        destination_path = to_stored_path(
            Path("exports") / "render_exports" / project.id / f"job_{job.id}.{ext}"
        )

        storage = get_storage_provider()

        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            artifact = dispatch_render(context, tmp_path)
            
            # Persist to storage
            content = tmp_path.read_bytes()
            final_path = storage.store(content, destination_path)

            job.status = RenderStatus.COMPLETED.value
            job.output_path = final_path
            job.result_message = artifact.message
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    except Exception:  # noqa: BLE001
        logger.exception("Render job failed: %s", job.id)
        job.status = RenderStatus.FAILED.value
        job.result_message = "Render job failed. Review the draft content and retry."

    db.commit()
    db.refresh(job)
    return job


def build_render_job_payload(db: Session, job: RenderJob) -> dict[str, object]:
    from unifoli_api.services.async_job_service import get_latest_job_for_resource

    settings = get_settings()
    try:
        template = _resolve_selected_template(
            render_format=RenderFormat(job.render_format),
            template_id=job.template_id,
        )
        template_label = template.label
        template_id = template.id
    except ValueError:
        template_label = None
        template_id = job.template_id

    async_job = get_latest_job_for_resource(db, resource_type="render_job", resource_id=job.id)
    return {
        "id": job.id,
        "project_id": job.project_id,
        "draft_id": job.draft_id,
        "render_format": job.render_format,
        "template_id": template_id,
        "template_label": template_label,
        "include_provenance_appendix": job.include_provenance_appendix,
        "hide_internal_provenance_on_final_export": job.hide_internal_provenance_on_final_export,
        "status": job.status,
        "download_url": f"{settings.api_prefix}/render-jobs/{job.id}/download" if job.output_path else None,
        "result_message": job.result_message,
        "requested_by": job.requested_by,
        "async_job_id": async_job.id if async_job else None,
        "async_job_status": async_job.status if async_job else None,
        "progress_stage": async_job.progress_stage if async_job else None,
        "progress_message": async_job.progress_message if async_job else None,
        "retry_count": async_job.retry_count if async_job else 0,
        "max_retries": async_job.max_retries if async_job else 0,
        "failure_reason": async_job.failure_reason if async_job else None,
        "dead_lettered_at": async_job.dead_lettered_at if async_job else None,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
