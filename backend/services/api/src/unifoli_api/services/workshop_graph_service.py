from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkshopGraphPhase(StrEnum):
    SUBJECT_INPUT = "subject_input"
    TOPIC_RECOMMENDATION = "topic_recommendation"
    TOPIC_SELECTION = "topic_selection"
    OUTLINE_GENERATION = "outline_generation"
    OUTLINE_SELECTION = "outline_selection"
    RESEARCH_GENERATION = "research_generation"
    RESEARCH_SELECTION = "research_selection"
    PATCH_GENERATION = "patch_generation"
    PATCH_REVIEW = "patch_review"
    PATCH_APPLIED = "patch_applied"
    FREEFORM_COAUTHORING = "freeform_coauthoring"


class WorkshopGraphState(BaseModel):
    project_id: str | None = None
    workshop_id: str | None = None
    user_id: str | None = None
    phase: WorkshopGraphPhase = WorkshopGraphPhase.SUBJECT_INPUT
    selected_topic_id: str | None = None
    selected_outline_id: str | None = None
    selected_research_candidate_ids: list[str] = Field(default_factory=list)
    structured_draft: dict[str, Any] | None = None
    pending_patch: dict[str, Any] | None = None
    source_ids: list[str] = Field(default_factory=list)
    format_profile: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class WorkshopGraphEvent(BaseModel):
    type: Literal[
        "subject_submitted",
        "topic_recommended",
        "topic_selected",
        "outline_generated",
        "outline_selected",
        "research_generated",
        "research_selected",
        "patch_generated",
        "patch_accepted",
        "patch_rejected",
        "freeform_message",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkshopGraphResult(BaseModel):
    state: WorkshopGraphState
    emitted_events: list[WorkshopGraphEvent] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None


_NEXT_PHASE_BY_EVENT: dict[str, WorkshopGraphPhase] = {
    "subject_submitted": WorkshopGraphPhase.TOPIC_RECOMMENDATION,
    "topic_recommended": WorkshopGraphPhase.TOPIC_SELECTION,
    "topic_selected": WorkshopGraphPhase.OUTLINE_GENERATION,
    "outline_generated": WorkshopGraphPhase.OUTLINE_SELECTION,
    "outline_selected": WorkshopGraphPhase.RESEARCH_GENERATION,
    "research_generated": WorkshopGraphPhase.RESEARCH_SELECTION,
    "research_selected": WorkshopGraphPhase.PATCH_GENERATION,
    "patch_generated": WorkshopGraphPhase.PATCH_REVIEW,
    "patch_accepted": WorkshopGraphPhase.PATCH_APPLIED,
    "patch_rejected": WorkshopGraphPhase.FREEFORM_COAUTHORING,
    "freeform_message": WorkshopGraphPhase.FREEFORM_COAUTHORING,
}


def run_workshop_graph_step(
    state: WorkshopGraphState,
    event: WorkshopGraphEvent,
) -> WorkshopGraphResult:
    """Small deterministic skeleton for a future LangGraph-backed workshop flow."""

    next_state = state.model_copy(deep=True)
    next_state.phase = _NEXT_PHASE_BY_EVENT.get(event.type, state.phase)

    if event.type == "topic_selected":
        next_state.selected_topic_id = _string_payload(event, "topic_id")
    elif event.type == "outline_selected":
        next_state.selected_outline_id = _string_payload(event, "outline_id")
    elif event.type == "research_selected":
        next_state.selected_research_candidate_ids = _string_list_payload(event, "research_candidate_ids")
        next_state.source_ids = _string_list_payload(event, "source_ids")
    elif event.type == "patch_generated":
        next_state.pending_patch = event.payload.get("patch") if isinstance(event.payload.get("patch"), dict) else None
    elif event.type == "patch_accepted":
        next_state.pending_patch = None
    elif event.type == "patch_rejected":
        next_state.pending_patch = None

    actions = _build_next_actions(next_state)
    return WorkshopGraphResult(
        state=next_state,
        emitted_events=[event],
        actions=actions,
        message=_phase_message(next_state.phase),
    )


def _string_payload(event: WorkshopGraphEvent, key: str) -> str | None:
    value = event.payload.get(key)
    return str(value).strip() if value else None


def _string_list_payload(event: WorkshopGraphEvent, key: str) -> list[str]:
    value = event.payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _build_next_actions(state: WorkshopGraphState) -> list[dict[str, Any]]:
    if state.phase == WorkshopGraphPhase.PATCH_REVIEW and state.pending_patch:
        return [
            {"type": "show_patch_review", "patch": state.pending_patch},
            {"type": "wait_for_user_approval"},
        ]
    if state.phase == WorkshopGraphPhase.RESEARCH_SELECTION:
        return [{"type": "show_research_candidates"}]
    return []


def _phase_message(phase: WorkshopGraphPhase) -> str:
    return {
        WorkshopGraphPhase.SUBJECT_INPUT: "Waiting for a subject or broad area.",
        WorkshopGraphPhase.TOPIC_RECOMMENDATION: "Ready to recommend topic cards.",
        WorkshopGraphPhase.TOPIC_SELECTION: "Waiting for the student to select a topic.",
        WorkshopGraphPhase.OUTLINE_GENERATION: "Ready to generate outline candidates.",
        WorkshopGraphPhase.OUTLINE_SELECTION: "Waiting for outline selection.",
        WorkshopGraphPhase.RESEARCH_GENERATION: "Ready to generate research candidates.",
        WorkshopGraphPhase.RESEARCH_SELECTION: "Waiting for research candidate selection.",
        WorkshopGraphPhase.PATCH_GENERATION: "Ready to generate a document patch.",
        WorkshopGraphPhase.PATCH_REVIEW: "Waiting for patch review.",
        WorkshopGraphPhase.PATCH_APPLIED: "Patch was accepted and can be persisted.",
        WorkshopGraphPhase.FREEFORM_COAUTHORING: "Continuing freeform coauthoring.",
    }[phase]
