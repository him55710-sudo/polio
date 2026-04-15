from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from unifoli_api.core.security import sanitize_public_error
from unifoli_api.schemas.pipeline_metadata import PipelineMetadata

_DOCUMENT_ERROR_FALLBACK = "Document processing failed. Retry after checking the uploaded file."


def _sanitize_parse_metadata(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}

    try:
        # Use our new schema for robust validation and sanitization
        validated = PipelineMetadata.from_dict(value)
        return validated.model_dump(exclude_none=True)
    except Exception:
        # Fallback to empty if validation fails completely
        return {}


class ParsedDocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    upload_asset_id: str
    original_filename: str | None
    content_type: str | None
    file_size_bytes: int | None
    upload_status: str | None
    parser_name: str
    source_extension: str
    status: str
    masking_status: str
    parse_attempts: int
    last_error: str | None
    can_retry: bool
    latest_async_job_id: str | None
    latest_async_job_status: str | None
    latest_async_job_error: str | None
    page_count: int
    word_count: int
    parse_started_at: datetime | None
    parse_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("last_error", "latest_async_job_error", mode="before")
    @classmethod
    def sanitize_error_fields(cls, value: object) -> str | None:
        if value is None:
            return None
        return sanitize_public_error(str(value), fallback=_DOCUMENT_ERROR_FALLBACK)


class ParsedDocumentRead(ParsedDocumentSummary):
    content_text: str
    content_markdown: str
    parse_metadata: dict[str, object]

    @field_validator("parse_metadata", mode="before")
    @classmethod
    def sanitize_parse_metadata(cls, value: object) -> dict[str, object]:
        return _sanitize_parse_metadata(value)


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    project_id: str
    chunk_index: int
    page_number: int | None
    char_start: int
    char_end: int
    token_estimate: int
    content_text: str
    embedding_model: str | None
    created_at: datetime
