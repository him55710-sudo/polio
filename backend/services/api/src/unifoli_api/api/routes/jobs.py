from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from unifoli_api.api.deps import get_current_user, get_db
from unifoli_api.core.config import get_settings
from unifoli_api.core.rate_limit import rate_limit
from unifoli_api.db.models.user import User
from unifoli_api.schemas.async_job import AsyncJobRead, as_async_job_read
from unifoli_api.services.async_job_service import (
    dispatch_job_if_enabled,
    get_async_job,
    get_latest_job_for_resource,
    list_project_jobs,
    process_async_job,
    process_next_async_job,
    retry_async_job,
)
from unifoli_api.services.project_service import get_project

router = APIRouter()
logger = logging.getLogger("unifoli.api.jobs")


def _authorize_job_access(db: Session, job, current_user: User) -> None:
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.project_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Job is not bound to a project.")
    project = get_project(db, job.project_id, owner_user_id=current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")


@router.get("", response_model=list[AsyncJobRead])
def list_jobs_route(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AsyncJobRead]:
    project = get_project(db, project_id, owner_user_id=current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return [as_async_job_read(item) for item in list_project_jobs(db, project_id)]


@router.get("/resource/{resource_type}/{resource_id}", response_model=AsyncJobRead)
def get_latest_resource_job_route(
    resource_type: str,
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncJobRead:
    job = get_latest_job_for_resource(db, resource_type=resource_type, resource_id=resource_id)
    _authorize_job_access(db, job, current_user)
    return as_async_job_read(job)


@router.get("/{job_id}", response_model=AsyncJobRead)
def get_job_route(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncJobRead:
    job = get_async_job(db, job_id)
    _authorize_job_access(db, job, current_user)
    return as_async_job_read(job)


@router.post("/{job_id}/retry", response_model=AsyncJobRead)
def retry_job_route(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit(bucket="async_job_retry", limit=10, window_seconds=300)),
) -> AsyncJobRead:
    job = get_async_job(db, job_id)
    _authorize_job_access(db, job, current_user)
    retried = retry_async_job(db, job_id)
    if retried is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    dispatch_job_if_enabled(retried.id)
    return as_async_job_read(retried)


@router.post("/{job_id}/process", response_model=AsyncJobRead)
def process_job_route(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit(bucket="async_job_process", limit=20, window_seconds=300)),
) -> AsyncJobRead:
    settings = get_settings()
    if not settings.allow_inline_job_processing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inline job processing is disabled. Use the worker instead.",
        )
    job = get_async_job(db, job_id)
    _authorize_job_access(db, job, current_user)
    processed = process_async_job(db, job_id)
    if processed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return as_async_job_read(processed)

@router.post("/cron/process", response_model=dict[str, object])
def cron_process_jobs_route(
    request: Request,
    cron_secret: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """
    Dedicated endpoint for scheduled cron jobs to pump the async job queue.
    Supports Vercel's standard CRON_SECRET via Authorization header or query param.
    """
    settings = get_settings()
    from unifoli_api.core.database import utc_now
    
    # Authenticate cron request
    auth_header = request.headers.get("Authorization", "")
    bearer_secret = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    effective_secret = cron_secret or bearer_secret
    
    if settings.app_cron_secret and effective_secret != settings.app_cron_secret:
        logger.warning("Unauthorized cron attempt rejected.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret.")
    
    # Run a round of processing
    processed_count = 0
    max_batch = 5
    for _ in range(max_batch):
        job = process_next_async_job(db)
        if job is None:
            break
        processed_count += 1
    
    return {
        "status": "ok",
        "processed_count": processed_count,
        "timestamp": utc_now().isoformat()
    }
