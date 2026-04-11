from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from unifoli_api.core.database import Base, utc_now
from unifoli_domain.enums import WorkshopStatus, TurnType, QualityLevel

if TYPE_CHECKING:
    from unifoli_api.db.models.project import Project


json_type = JSON().with_variant(JSONB, "postgresql")


class WorkshopSession(Base):
    __tablename__ = "workshop_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    quest_id: Mapped[str | None] = mapped_column(String, ForeignKey("quests.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=WorkshopStatus.IDLE.value)
    context_score: Mapped[int] = mapped_column(Integer, default=0)
    quality_level: Mapped[str] = mapped_column(String(8), default=QualityLevel.MID.value)  # low/mid/high
    stream_token: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    stream_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="workshop_sessions")
    turns: Mapped[list["WorkshopTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkshopTurn.created_at"
    )
    pinned_references: Mapped[list["PinnedReference"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    draft_artifacts: Mapped[list["DraftArtifact"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DraftArtifact.created_at"
    )

class WorkshopTurn(Base):
    __tablename__ = "workshop_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("workshop_sessions.id"), index=True, nullable=False)
    turn_type: Mapped[str] = mapped_column(String(32), default=TurnType.MESSAGE.value)  # starter, follow_up, message
    speaker_role: Mapped[str] = mapped_column(String(32), default="user")  # user, assistant, system
    query: Mapped[str] = mapped_column(Text(), nullable=False)
    response: Mapped[str | None] = mapped_column(Text(), nullable=True)
    action_payload: Mapped[dict | None] = mapped_column(json_type, nullable=True)  # Store structured choice info
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    session: Mapped["WorkshopSession"] = relationship(back_populates="turns")

class PinnedReference(Base):
    __tablename__ = "pinned_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("workshop_sessions.id"), index=True, nullable=False)
    text_content: Mapped[str] = mapped_column(Text(), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["WorkshopSession"] = relationship(back_populates="pinned_references")


class DraftArtifact(Base):
    """?åÌÅ¨???åÎçîÎß?Í≤∞Í≥ºÎ¨?- UniFoli ?µÏã¨ ?∞Ï∂úÎ¨?""
    __tablename__ = "draft_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("workshop_sessions.id"), index=True, nullable=False)

    # ?µÏã¨ ?∞Ï∂úÎ¨??ÑÎìú
    report_markdown: Mapped[str | None] = mapped_column(Text(), nullable=True)           # ?êÍµ¨ Î≥¥Í≥†??Î≥∏Î¨∏
    teacher_record_summary_500: Mapped[str | None] = mapped_column(Text(), nullable=True)  # ?∏Ìäπ 500???îÏïΩ
    student_submission_note: Mapped[str | None] = mapped_column(Text(), nullable=True)   # ?ôÏÉù ?úÏ∂ú???∏Ìä∏
    evidence_map: Mapped[dict | None] = mapped_column(json_type, nullable=True)              # Ï¶ùÍ±∞ Îß?(?§Î™Ö Í∞Ä?•ÏÑ±)
    visual_specs: Mapped[list[dict]] = mapped_column(json_type, default=list, nullable=False)
    math_expressions: Mapped[list[dict]] = mapped_column(json_type, default=list, nullable=False)

    render_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/streaming/completed/failed
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # ?àÏ†Ñ???àÏßà Î©îÌ??∞Ïù¥??
    quality_level_applied: Mapped[str | None] = mapped_column(String(8), nullable=True)   # ?§Ï†ú ?ÅÏö©???òÏ?
    safety_score: Mapped[int | None] = mapped_column(Integer, nullable=True)               # 0~100 (?íÏùÑ?òÎ°ù ?àÏ†Ñ)
    safety_flags: Mapped[dict | None] = mapped_column(json_type, nullable=True)                # ?ÑÌóò ??™© ?ÅÏÑ∏
    quality_downgraded: Mapped[bool] = mapped_column(Boolean, default=False)               # Í∞ïÎì± ?¨Î?
    quality_control_meta: Mapped[dict | None] = mapped_column(json_type, nullable=True)    # ?àÏßà/?àÏ†Ñ Î©îÌ??∞Ïù¥??

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    session: Mapped["WorkshopSession"] = relationship(back_populates="draft_artifacts")
