from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from polio_api.api.deps import get_current_user, get_db
from polio_api.core.config import get_settings
from polio_api.core.rate_limit import rate_limit
from polio_api.db.models.diagnosis_run import DiagnosisRun
from polio_api.db.models.project import Project
from polio_api.db.models.response_trace import ResponseTrace
from polio_api.db.models.user import User
from polio_api.schemas.draft import DraftCreate
from polio_api.schemas.diagnosis import (
    DiagnosisGuidedPlanRequest,
    DiagnosisGuidedPlanResponse,
    DiagnosisPolicyFlagRead,
    DiagnosisResultPayload,
    DiagnosisRunRequest,
    DiagnosisRunResponse,
)
from polio_api.services.async_job_service import (
    create_async_job,
    dispatch_job_if_enabled,
    get_latest_job_for_resource,
    process_async_job,
)
from polio_api.services.diagnosis_runtime_service import build_policy_scan_text, combine_project_text
from polio_api.services.diagnosis_service import (
    DiagnosisCitation,
    attach_policy_flags_to_run,
    build_guided_outline_plan,
    detect_policy_flags,
    ensure_review_task_for_flags,
    latest_response_trace,
    serialize_citation,
    serialize_policy_flag,
)
from polio_api.services.draft_service import create_draft
from polio_api.services.project_service import get_project
from polio_domain.enums import AsyncJobType

router = APIRouter()


def _get_run_for_user(db: Session, diagnosis_id: str, user_id: str) -> DiagnosisRun | None:
    return db.scalar(
        select(DiagnosisRun)
        .join(Project, DiagnosisRun.project_id == Project.id)
        .where(DiagnosisRun.id == diagnosis_id, Project.owner_user_id == user_id)
        .options(
            selectinload(DiagnosisRun.policy_flags),
            selectinload(DiagnosisRun.review_tasks),
            selectinload(DiagnosisRun.response_traces).selectinload(ResponseTrace.citations),
        )
    )


def _build_run_response(db: Session, run: DiagnosisRun) -> DiagnosisRunResponse:
    payload = DiagnosisResultPayload.model_validate_json(run.result_payload) if run.result_payload else None
    trace = latest_response_trace(run)
    citations = [DiagnosisCitation.model_validate(serialize_citation(item)) for item in (trace.citations if trace else [])]
    async_job = get_latest_job_for_resource(db, resource_type="diagnosis_run", resource_id=run.id)
    return DiagnosisRunResponse(
        id=run.id,
        project_id=run.project_id,
        status=run.status,
        result_payload=payload,
        error_message=run.error_message,
        review_required=bool(run.review_tasks or run.policy_flags),
        policy_flags=[DiagnosisPolicyFlagRead.model_validate(serialize_policy_flag(item)) for item in run.policy_flags],
        citations=citations,
        response_trace_id=trace.id if trace else None,
        async_job_id=async_job.id if async_job else None,
        async_job_status=async_job.status if async_job else None,
    )


@router.post("/run", response_model=DiagnosisRunResponse)
@router.post("/runs", response_model=DiagnosisRunResponse)
async def trigger_diagnosis(
    payload: DiagnosisRunRequest,
    wait_for_completion: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit(bucket="diagnosis_runs", limit=10, window_seconds=300, guest_limit=2)),
) -> DiagnosisRunResponse:
    settings = get_settings()
    if wait_for_completion and not settings.allow_inline_job_processing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inline job processing is disabled. Use the worker instead.",
        )

    project = get_project(db, payload.project_id, owner_user_id=current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    documents, full_text = combine_project_text(project.id, db)
    policy_scan_text = build_policy_scan_text(documents) or full_text

    run = DiagnosisRun(project_id=payload.project_id, status="PENDING")
    db.add(run)
    db.flush()

    findings = detect_policy_flags(policy_scan_text)
    flag_records = attach_policy_flags_to_run(db, run=run, project=project, user=current_user, findings=findings)
    review_task = ensure_review_task_for_flags(db, run=run, project=project, user=current_user, findings=findings)
    db.commit()
    db.refresh(run)

    async_job = create_async_job(
        db,
        job_type=AsyncJobType.DIAGNOSIS.value,
        resource_type="diagnosis_run",
        resource_id=run.id,
        project_id=payload.project_id,
        payload={
            "run_id": run.id,
            "project_id": payload.project_id,
            "owner_user_id": current_user.id,
            "fallback_target_university": current_user.target_university or project.target_university,
            "fallback_target_major": current_user.target_major or project.target_major,
        },
    )
    if wait_for_completion:
        process_async_job(db, async_job.id)
        completed_run = _get_run_for_user(db, run.id, current_user.id)
        if completed_run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis run not found.")
        return _build_run_response(db, completed_run)

    dispatch_job_if_enabled(async_job.id)

    return DiagnosisRunResponse(
        id=run.id,
        project_id=run.project_id,
        status=run.status,
        review_required=review_task is not None,
        policy_flags=[DiagnosisPolicyFlagRead.model_validate(serialize_policy_flag(item)) for item in flag_records],
        async_job_id=async_job.id,
        async_job_status=async_job.status,
    )


@router.post("/{diagnosis_id}/guided-plan", response_model=DiagnosisGuidedPlanResponse)
@router.post("/runs/{diagnosis_id}/guided-plan", response_model=DiagnosisGuidedPlanResponse)
async def build_guided_plan_route(
    diagnosis_id: str,
    payload: DiagnosisGuidedPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosisGuidedPlanResponse:
    run = _get_run_for_user(db, diagnosis_id, current_user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis run not found.")
    if not run.result_payload:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Diagnosis results are not ready yet.")

    result = DiagnosisResultPayload.model_validate_json(run.result_payload)
    try:
        direction, topic, outline = build_guided_outline_plan(
            result=result,
            direction_id=payload.direction_id,
            topic_id=payload.topic_id,
            page_count=payload.page_count,
            export_format=payload.export_format,
            template_id=payload.template_id,
            include_provenance_appendix=payload.include_provenance_appendix,
            hide_internal_provenance_on_final_export=payload.hide_internal_provenance_on_final_export,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if payload.open_text_note:
        outline.outline_markdown = (
            f"{outline.outline_markdown}\n\n## Optional Student Note\n{payload.open_text_note.strip()}"
        )

    draft = create_draft(
        db,
        project_id=run.project_id,
        payload=DraftCreate(
            title=topic.title,
            content_markdown=outline.outline_markdown,
        ),
    )
    outline.draft_id = draft.id
    outline.draft_title = draft.title
    return DiagnosisGuidedPlanResponse(
        diagnosis_run_id=run.id,
        project_id=run.project_id,
        direction=direction,
        topic=topic,
        outline=outline,
    )


@router.get("/{diagnosis_id}", response_model=DiagnosisRunResponse)
@router.get("/runs/{diagnosis_id}", response_model=DiagnosisRunResponse)
async def get_diagnosis_status(
    diagnosis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosisRunResponse:
    run = _get_run_for_user(db, diagnosis_id, current_user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis run not found.")
    return _build_run_response(db, run)
@router.get("/project/{project_id}/latest", response_model=DiagnosisRunResponse)
async def get_latest_diagnosis_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosisRunResponse:
    run = db.scalar(
        select(DiagnosisRun)
        .join(Project, DiagnosisRun.project_id == Project.id)
        .where(Project.id == project_id, Project.owner_user_id == current_user.id)
        .order_by(DiagnosisRun.created_at.desc())
        .limit(1)
        .options(
            selectinload(DiagnosisRun.policy_flags),
            selectinload(DiagnosisRun.review_tasks),
            selectinload(DiagnosisRun.response_traces).selectinload(ResponseTrace.citations),
        )
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No diagnosis run found for this project.")
    return _build_run_response(db, run)
