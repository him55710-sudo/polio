from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from polio_api.services.diagnosis_service import (
    DiagnosisCitation,
    DiagnosisResult,
    GuidedDraftOutline,
    RecommendedDirection,
    TopicCandidate,
)


class DiagnosisRunRequest(BaseModel):
    project_id: str


class DiagnosisResultPayload(DiagnosisResult):
    pass


class DiagnosisGuidedPlanRequest(BaseModel):
    direction_id: str = Field(min_length=1, max_length=80)
    topic_id: str = Field(min_length=1, max_length=80)
    page_count: int = Field(ge=5, le=20)
    export_format: Literal["pdf", "pptx", "hwpx"]
    template_id: str = Field(min_length=1, max_length=80)
    include_provenance_appendix: bool = False
    hide_internal_provenance_on_final_export: bool = True
    open_text_note: str | None = Field(default=None, max_length=1000)


class DiagnosisGuidedPlanResponse(BaseModel):
    diagnosis_run_id: str
    project_id: str
    direction: RecommendedDirection
    topic: TopicCandidate
    outline: GuidedDraftOutline


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
