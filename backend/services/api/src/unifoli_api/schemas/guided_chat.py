from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GuidedConversationPhase = Literal[
    "subject_input",
    "specific_topic_check",
    "topic_recommendation",
    "topic_selection",
    "page_range_selection",
    "structure_selection",
    "drafting_next_step",
    "freeform_coauthoring",
]


class GuidedChoiceOption(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=240)
    value: str | None = Field(default=None, max_length=240)


class GuidedChoiceGroup(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    style: Literal["cards", "chips", "buttons"] = "cards"
    options: list[GuidedChoiceOption] = Field(default_factory=list)


class GuidedChatStartRequest(BaseModel):
    project_id: str | None = None


class GuidedChatStartResponse(BaseModel):
    greeting: str
    assistant_message: str | None = None
    phase: GuidedConversationPhase = "subject_input"
    project_id: str | None = None
    evidence_gap_note: str | None = None
    choice_groups: list[GuidedChoiceGroup] = Field(default_factory=list)
    limited_mode: bool | None = None
    limited_reason: str | None = None
    state_summary: dict[str, Any] | None = None


class TopicSuggestion(BaseModel):
    id: str
    title: str
    one_line_summary: str | None = None
    why_fit_student: str
    link_to_record_flow: str
    link_to_target_major_or_university: str | None = None
    novelty_point: str | None = None
    caution_note: str | None = None
    record_connection_point: str | None = None
    deepening_point: str | None = None
    career_connection_point: str | None = None
    social_issue_connection: str | None = None
    experiment_or_survey_method: str | None = None
    expected_output: str | None = None
    outline_draft: list[str] = Field(default_factory=list)
    admissions_strength: str | None = None
    risk_or_supplement: str | None = None
    scores: dict[str, int] = Field(default_factory=dict)
    total_score: int | None = None
    topic_band: Literal["safe", "challenging"] | None = None
    suggestion_type: Literal["interest", "subject", "major"] | None = None
    is_starred: bool = False


class TopicSuggestionRequest(BaseModel):
    project_id: str | None = None
    subject: str = Field(min_length=1, max_length=100)
    starred_keywords: list[str] = Field(default_factory=list)
    target_major: str | None = None


class TopicSuggestionResponse(BaseModel):
    greeting: str
    assistant_message: str | None = None
    phase: GuidedConversationPhase = "topic_selection"
    subject: str
    suggestions: list[TopicSuggestion]
    evidence_gap_note: str | None = None
    choice_groups: list[GuidedChoiceGroup] = Field(default_factory=list)
    limited_mode: bool | None = None
    limited_reason: str | None = None
    state_summary: dict[str, Any] | None = None


class PageRangeOption(BaseModel):
    label: str
    min_pages: int = Field(ge=1, le=20)
    max_pages: int = Field(ge=1, le=20)
    why_this_length: str


class OutlineSection(BaseModel):
    title: str
    purpose: str


class TopicSelectionRequest(BaseModel):
    project_id: str | None = None
    selected_topic_id: str = Field(min_length=1, max_length=120)
    subject: str | None = Field(default=None, max_length=100)
    suggestions: list[TopicSuggestion] = Field(default_factory=list)


class TopicSelectionResponse(BaseModel):
    phase: GuidedConversationPhase = "page_range_selection"
    assistant_message: str | None = None
    selected_topic_id: str
    selected_title: str
    recommended_page_ranges: list[PageRangeOption]
    recommended_outline: list[OutlineSection]
    starter_draft_markdown: str
    guidance_message: str
    structure_options: list[GuidedChoiceOption] = Field(default_factory=list)
    next_action_options: list[GuidedChoiceOption] = Field(default_factory=list)
    choice_groups: list[GuidedChoiceGroup] = Field(default_factory=list)
    limited_mode: bool | None = None
    limited_reason: str | None = None
    state_summary: dict[str, Any] | None = None


class PageRangeSelectionRequest(BaseModel):
    project_id: str | None = None
    selected_page_range_label: str = Field(min_length=1, max_length=120)
    selected_topic_id: str | None = Field(default=None, min_length=1, max_length=120)


class PageRangeSelectionResponse(BaseModel):
    phase: GuidedConversationPhase = "structure_selection"
    assistant_message: str
    selected_page_range_label: str
    selected_page_range_note: str | None = None
    structure_options: list[GuidedChoiceOption] = Field(default_factory=list)
    choice_groups: list[GuidedChoiceGroup] = Field(default_factory=list)
    limited_mode: bool | None = None
    limited_reason: str | None = None
    state_summary: dict[str, Any] | None = None


class StructureSelectionRequest(BaseModel):
    project_id: str | None = None
    selected_structure_id: str = Field(min_length=1, max_length=120)


class StructureSelectionResponse(BaseModel):
    phase: GuidedConversationPhase = "drafting_next_step"
    assistant_message: str
    selected_structure_id: str
    selected_structure_label: str
    next_action_options: list[GuidedChoiceOption] = Field(default_factory=list)
    choice_groups: list[GuidedChoiceGroup] = Field(default_factory=list)
    limited_mode: bool | None = None
    limited_reason: str | None = None
    state_summary: dict[str, Any] | None = None


class GuidedChatStatePayload(BaseModel):
    phase: GuidedConversationPhase = "subject_input"
    subject: str | None = None
    suggestions: list[TopicSuggestion] = Field(default_factory=list)
    selected_topic_id: str | None = None
    selected_page_range_label: str | None = None
    selected_structure_id: str | None = None
    recommended_page_ranges: list[PageRangeOption] = Field(default_factory=list)
    recommended_outline: list[OutlineSection] = Field(default_factory=list)
    structure_options: list[GuidedChoiceOption] = Field(default_factory=list)
    next_action_options: list[GuidedChoiceOption] = Field(default_factory=list)
    starter_draft_markdown: str | None = None
    state_summary: dict[str, Any] = Field(default_factory=dict)
    limited_mode: bool | None = None
    limited_reason: str | None = None


class TopicStarToggleRequest(BaseModel):
    project_id: str | None = None
    topic_id: str
    is_starred: bool
    topic_title: str | None = None
