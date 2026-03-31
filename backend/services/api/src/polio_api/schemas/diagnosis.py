from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from polio_api.services.diagnosis_service import DiagnosisCitation, DiagnosisResult


class DiagnosisRunRequest(BaseModel):
    project_id: str


class DiagnosisResultPayload(DiagnosisResult):
    pass


class DiagnosisPolicyFlagRead(BaseModel):
    id: str
    code: str
    severity: str
    detail: str
    matched_text: str
    match_count: int
    status: str
    created_at: datetime | None = None


class DiagnosisRunResponse(BaseModel):
    id: str
    project_id: str
    status: str
    result_payload: DiagnosisResultPayload | None = None
    error_message: str | None = None
    review_required: bool = False
    policy_flags: list[DiagnosisPolicyFlagRead] = Field(default_factory=list)
    citations: list[DiagnosisCitation] = Field(default_factory=list)
    response_trace_id: str | None = None
    async_job_id: str | None = None
    async_job_status: str | None = None
