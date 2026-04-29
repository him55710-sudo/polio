from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AsyncJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str | None
    job_type: str
    resource_type: str
    resource_id: str
    status: str
    retry_count: int
    max_retries: int
    failure_reason: str | None
    failure_history: list[dict[str, object]]
    
    # Advanced stabilization fields
    phase: str | None = None
    stale: bool = False
    retryable: bool = False
    failure_code: str | None = None
    public_message: str | None = None
    debug_detail: str | None = None
    
    progress_stage: str | None = None
    progress_message: str | None = None
    progress_percent: float | None = None
    progress_history: list[dict[str, object]] = Field(default_factory=list)
    
    heartbeat_at: datetime | None = None
    next_retry_at: datetime | None = None
    
    attempt_count: int = 0
    max_attempts: int = 0
    
    next_attempt_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    dead_lettered_at: datetime | None
    created_at: datetime
    updated_at: datetime


def as_async_job_read(job: object) -> AsyncJobRead:
    # Use model_validate to handle core fields
    base = AsyncJobRead.model_validate(job)
    
    # Calculate derived fields
    status = str(getattr(job, "status", "")).upper()
    retry_count = int(getattr(job, "retry_count", 0))
    max_retries = int(getattr(job, "max_retries", 0))
    updated_at = getattr(job, "updated_at", None)
    
    # Heartbeat and Stale logic
    base.heartbeat_at = updated_at
    base.attempt_count = retry_count + 1 if status == "RUNNING" else retry_count
    base.max_attempts = max_retries + 1
    base.next_retry_at = getattr(job, "next_attempt_at", None)
    
    if status == "RUNNING" and updated_at:
        # If running but not updated for 2 minutes, consider it potentially stale
        from unifoli_api.core.config import get_settings
        settings = get_settings()
        stale_threshold = getattr(settings, "async_job_stale_after_seconds", 300)
        is_stale = (utc_now() - updated_at).total_seconds() > stale_threshold
        base.stale = is_stale
    
    # Calculate retryable
    base.retryable = (
        status in {"FAILED", "STALE_FAILED", "RETRYING"} 
        and retry_count < max_retries
    )
    
    # Map from DB columns
    base.phase = getattr(job, "phase", None)
    base.failure_code = getattr(job, "failure_code", None)
    
    # Fallback to payload or logic
    payload = getattr(job, "payload", None)
    if isinstance(payload, dict):
        if not base.phase:
            base.phase = str(payload.get("phase") or "").lower() or None
        if not base.failure_code:
            base.failure_code = str(payload.get("failure_code") or "").upper() or None
            
        base.public_message = str(payload.get("public_message") or "").strip() or None
        base.debug_detail = str(payload.get("debug_detail") or "").strip() or None
        
        percent = payload.get("progress_percent")
        if isinstance(percent, (int, float)):
            base.progress_percent = float(percent)
        
        history = payload.get("progress_history")
        if isinstance(history, list):
            normalized_history: list[dict[str, object]] = []
            for item in history:
                if not isinstance(item, dict):
                    continue
                stage = str(item.get("stage") or "").strip()
                message = str(item.get("message") or "").strip()
                completed_at = str(item.get("completed_at") or "").strip()
                if not stage and not message:
                    continue
                normalized_history.append(
                    {
                        "stage": stage or "stage",
                        "message": message or "",
                        "completed_at": completed_at or "",
                    }
                )
            base.progress_history = normalized_history[-20:]
            
    # Default public message if failed
    if status == "FAILED" and not base.public_message:
        base.public_message = "작업 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        
    return base

