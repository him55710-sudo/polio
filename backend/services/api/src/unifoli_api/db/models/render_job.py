from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from unifoli_api.core.database import Base
from unifoli_domain.enums import RenderStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RenderJob(Base):
    __tablename__ = "render_jobs"
    __table_args__ = (
        Index("ix_render_jobs_project_created_at", "project_id", "created_at"),
        Index("ix_render_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"), index=True)
    render_format: Mapped[str] = mapped_column(String(16))
    template_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    include_provenance_appendix: Mapped[bool] = mapped_column(Boolean, default=False)
    hide_internal_provenance_on_final_export: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default=RenderStatus.QUEUED.value)
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="render_jobs")
    draft: Mapped["Draft"] = relationship(back_populates="render_jobs")
