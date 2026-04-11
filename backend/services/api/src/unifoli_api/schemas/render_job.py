from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from unifoli_domain.enums import RenderFormat


class RenderTemplatePreviewInfo(BaseModel):
    accent_color: str
    surface_tone: str
    cover_title: str
    preview_sections: list[str]
    thumbnail_hint: str


class RenderTemplateInfo(BaseModel):
    id: str
    label: str
    description: str
    supported_formats: list[RenderFormat]
    category: str
    section_schema: list[str]
    density: str
    visual_priority: str
    supports_provenance_appendix: bool
    recommended_for: list[str]
    preview: RenderTemplatePreviewInfo


class RenderJobCreate(BaseModel):
    project_id: str
    draft_id: str
    render_format: RenderFormat
    template_id: str | None = Field(default=None, max_length=80)
    include_provenance_appendix: bool = False
    hide_internal_provenance_on_final_export: bool = True
    requested_by: str | None = Field(default=None, max_length=120)


class RenderJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    draft_id: str
    render_format: str
    template_id: str | None = None
    template_label: str | None = None
    include_provenance_appendix: bool = False
    hide_internal_provenance_on_final_export: bool = True
    status: str
    download_url: str | None
    result_message: str | None
    requested_by: str | None
    async_job_id: str | None = None
    async_job_status: str | None = None
    progress_stage: str | None = None
    progress_message: str | None = None
    retry_count: int = 0
    max_retries: int = 0
    failure_reason: str | None = None
    dead_lettered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RenderFormatInfo(BaseModel):
    format: RenderFormat
    implementation_level: str
    description: str
    default_template_id: str
