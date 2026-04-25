from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from unifoli_api.core.security import sanitize_public_error
from unifoli_api.schemas.async_job import AsyncJobRead
from unifoli_domain.enums import ResearchSourceClassification


class ResearchSourceCreate(BaseModel):
    source_type: Literal["web_article", "youtube_transcript", "paper", "pdf_document"]
    source_classification: ResearchSourceClassification = ResearchSourceClassification.EXPERT_COMMENTARY
    title: str | None = Field(default=None, max_length=500)
    canonical_url: str | None = Field(default=None, max_length=1000)
    text: str | None = Field(default=None, max_length=100000)
    html_content: str | None = Field(default=None, max_length=200000)
    transcript_segments: list[str] = Field(default_factory=list, max_length=200)
    abstract: str | None = Field(default=None, max_length=10000)
    extracted_text: str | None = Field(default=None, max_length=100000)
    publisher: str | None = Field(default=None, max_length=255)
    author_names: list[str] = Field(default_factory=list, max_length=20)
    published_on: date | None = None
    external_id: str | None = Field(default=None, max_length=255)
    usage_note: str | None = Field(default=None, max_length=500)
    copyright_note: str | None = Field(default=None, max_length=500)
    metadata: dict[str, object] = Field(default_factory=dict)


class ResearchIngestRequest(BaseModel):
    project_id: str
    items: list[ResearchSourceCreate] = Field(min_length=1, max_length=10)


class ResearchDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    provenance_type: str
    source_type: str
    source_classification: str
    trust_rank: int
    title: str
    canonical_url: str | None
    external_id: str | None
    publisher: str | None
    published_on: date | None
    usage_note: str | None
    copyright_note: str | None
    content_hash: str
    parser_name: str
    status: str
    last_error: str | None
    author_names: list[str]
    source_metadata: dict[str, object]
    chunk_count: int
    word_count: int
    ingested_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("last_error", mode="before")
    @classmethod
    def sanitize_last_error(cls, value: object) -> str | None:
        if value is None:
            return None
        return sanitize_public_error(
            str(value),
            fallback="Research ingestion failed. Retry after checking the provided source data.",
        )


class ResearchChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    project_id: str
    provenance_type: str
    chunk_index: int
    char_start: int
    char_end: int
    token_estimate: int
    content_text: str
    embedding_model: str | None
    created_at: datetime


class ResearchIngestResponse(BaseModel):
    documents: list[ResearchDocumentRead]
    jobs: list[AsyncJobRead]


class ResearchCrawlRequest(BaseModel):
    project_id: str
    urls: list[str] = Field(min_length=1, max_length=10)
    max_pages: int | None = Field(default=None, ge=1, le=5)
    max_chars_per_page: int | None = Field(default=None, ge=500, le=10000)


class CrawledPageRead(BaseModel):
    url: str
    title: str | None = None
    text: str | None = None
    markdown: str | None = None
    extracted_at: str
    provider: str
    status: Literal["ok", "error", "unavailable", "skipped"]
    error: str | None = None
    source_domain: str | None = None
    char_count: int = 0


class ResearchCrawlResponse(BaseModel):
    pages: list[CrawledPageRead]
    ok_count: int
    error_count: int
    unavailable_count: int
    skipped_count: int
    message: str | None = None
