from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from unifoli_api.core.database import Base, utc_now
from unifoli_domain.enums import QualityLevel, TurnType, WorkshopStatus

if TYPE_CHECKING:
    from unifoli_api.db.models.project import Project


json_type = JSON().with_variant(JSONB, "postgresql")


class WorkshopSession(Base):
    __tablename__ = "workshop_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    quest_id: Mapped[str | None] = mapped_column(String, ForeignKey("quests.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=WorkshopStatus.IDLE.value)
    context_score: Mapped[int] = mapped_column(Integer, default=0)
    quality_level: Mapped[str] = mapped_column(String(8), default=QualityLevel.MID.value)
    stream_token: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    stream_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="workshop_sessions")
    turns: Mapped[list["WorkshopTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkshopTurn.created_at",
    )
    pinned_references: Mapped[list["PinnedReference"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    draft_artifacts: Mapped[list["DraftArtifact"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DraftArtifact.created_at",
    )


class WorkshopTurn(Base):
    __tablename__ = "workshop_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workshop_sessions.id"),
        index=True,
        nullable=False,
    )
    turn_type: Mapped[str] = mapped_column(String(32), default=TurnType.MESSAGE.value)
    speaker_role: Mapped[str] = mapped_column(String(32), default="user")
    query: Mapped[str] = mapped_column(Text(), nullable=False)
    response: Mapped[str | None] = mapped_column(Text(), nullable=True)
    action_payload: Mapped[dict | None] = mapped_column(json_type, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    session: Mapped["WorkshopSession"] = relationship(back_populates="turns")


class PinnedReference(Base):
    __tablename__ = "pinned_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workshop_sessions.id"),
        index=True,
        nullable=False,
    )
    text_content: Mapped[str] = mapped_column(Text(), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["WorkshopSession"] = relationship(back_populates="pinned_references")


class DraftArtifact(Base):
    """Rendered workshop draft artifact for a session."""

    __tablename__ = "draft_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workshop_sessions.id"),
        index=True,
        nullable=False,
    )

    report_markdown: Mapped[str | None] = mapped_column(Text(), nullable=True)
    teacher_record_summary_500: Mapped[str | None] = mapped_column(Text(), nullable=True)
    student_submission_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    evidence_map: Mapped[dict | None] = mapped_column(json_type, nullable=True)
    visual_specs: Mapped[list[dict]] = mapped_column(json_type, default=list, nullable=False)
    math_expressions: Mapped[list[dict]] = mapped_column(json_type, default=list, nullable=False)

    render_status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)

    quality_level_applied: Mapped[str | None] = mapped_column(String(8), nullable=True)
    safety_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_flags: Mapped[dict | None] = mapped_column(json_type, nullable=True)
    quality_downgraded: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_control_meta: Mapped[dict | None] = mapped_column(json_type, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    session: Mapped["WorkshopSession"] = relationship(back_populates="draft_artifacts")
