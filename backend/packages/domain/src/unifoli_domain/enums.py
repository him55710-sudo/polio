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
    ?Œí¬??ê²°ê³¼ë¬¼ì˜ ê¹Šì´?€ ?œí˜„ ?˜ìœ„ë¥?ê²°ì •?˜ëŠ” ?ˆì§ˆ ?˜ì?.

    LOW  (?ˆì „??: êµê³¼ ê°œë… ì¶©ì‹¤, ê²€ì¦?ê°€?¥í•œ ?¬ì‹¤ ?„ì£¼, ?©íŠ¸ì²´í¬ ìµœìš°??
                   ?”ë ¤???œí˜„/?¬í™” ?´ë¡  ê¸ˆì?. ?„êµ¬???¤ì œë¡??´ë³¼ ???ˆëŠ” ?˜ì?.
    MID  (?œì???: êµê³¼ ?‘ìš© + ê°„ë‹¨???•ìž¥. ?¼ë°˜ ?™ìƒ???˜í–‰?ˆì„ ë²•í•œ ë²”ìœ„.
                   ì°¸ê³ ë¬¸í—Œ 1-2ê°??œìš© ê°€?? ?Œê²°ë¡??„ì¶œ ?ˆìš©.
    HIGH (?¬í™”??: ?¬í™” ?´ë¡  ?œìš© ê°€?¥í•˜??ë°˜ë“œ???™ìƒ ?¤ì œ ë§¥ë½ ê¸°ë°˜.
                   ì¶œì²˜ ê°•ì œ, AI ?„ìƒˆ ê°ì? ??ê°•ë“± ì¡°ì¹˜.
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
