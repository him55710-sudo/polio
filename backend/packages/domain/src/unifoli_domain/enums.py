# -*- coding: latin-1 -*-
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ProjectStatus(StrEnum):
    IDEA = "idea"
    ACTIVE = "active"
    ARCHIVED = "archived"


class UploadStatus(StrEnum):
    RECEIVED = "received"
    STORED = "stored"
    MASKING = "masking"
    PARSING = "parsing"
    RETRYING = "retrying"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"


class DocumentProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    MASKING = "masking"
    PARSING = "parsing"
    RETRYING = "retrying"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"


class DocumentMaskingStatus(StrEnum):
    PENDING = "pending"
    MASKING = "masking"
    MASKED = "masked"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    RETRYING = "retrying"


class DraftStatus(StrEnum):
    OUTLINE = "outline"
    IN_PROGRESS = "in_progress"
    READY_FOR_RENDER = "ready_for_render"
    ARCHIVED = "archived"


class RenderFormat(StrEnum):
    PDF = "pdf"
    PPTX = "pptx"
    HWPX = "hwpx"
    PORTFOLIO_DEV = "portfolio_dev"
    PORTFOLIO_ARCH = "portfolio_arch"


class RenderStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkshopStatus(StrEnum):
    IDLE = "idle"
    COLLECTING_CONTEXT = "collecting_context"
    DRAFTING = "drafting"
    RENDERING = "rendering"
    DONE = "done"


class TurnType(StrEnum):
    STARTER = "starter"
    FOLLOW_UP = "follow_up"
    MESSAGE = "message"


class QualityLevel(StrEnum):
    """
    ??크??결과물의 깊이?? ??현 ??위???결정??는 ??질 ????.

    LOW  (??전??: 교과 개념 충실, 검???가??한 ??실 ??주, ??트체크 최우??
                   ??려????현/??화 ??론 금??. ??구????제?????볼 ????는 ????.
    MID  (??????: 교과 ??용 + 간단????장. ??반 ??생????행??을 법한 범위.
                   참고문헌 1-2?????용 가?? ??결?????출 ??용.
    HIGH (??화??: ??화 ??론 ??용 가??하??반드????생 ??제 맥락 기반.
                   출처 강제, AI ??새 감?? ??강등 조치.
    """
    LOW  = "low"
    MID  = "mid"
    HIGH = "high"


class BlockType(StrEnum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"


class EvidenceProvenance(StrEnum):
    STUDENT_RECORD = "STUDENT_RECORD"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"


class ResearchSourceClassification(StrEnum):
    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    STUDENT_OWNED_SOURCE = "STUDENT_OWNED_SOURCE"
    EXPERT_COMMENTARY = "EXPERT_COMMENTARY"
    COMMUNITY_POST = "COMMUNITY_POST"
    SCRAPED_OPINION = "SCRAPED_OPINION"


class AsyncJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


class AsyncJobType(StrEnum):
    DIAGNOSIS = "diagnosis"
    DIAGNOSIS_REPORT = "diagnosis_report"
    DOCUMENT_PARSE = "document_parse"
    RENDER = "render"
    RESEARCH_INGEST = "research_ingest"
    INQUIRY_EMAIL = "inquiry_email"


class VisualApprovalStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    REPLACED = "replaced"
    REMOVED = "removed"
