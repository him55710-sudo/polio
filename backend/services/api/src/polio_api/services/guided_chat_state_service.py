from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from polio_api.db.models.draft import Draft
from polio_api.schemas.guided_chat import GuidedChatStatePayload
from polio_domain.enums import DraftStatus

GUIDED_CHAT_STATE_DRAFT_TITLE = "__guided_chat_state__"


def load_guided_chat_state(db: Session, project_id: str) -> GuidedChatStatePayload | None:
    state_draft = _get_state_draft(db, project_id)
    if state_draft is None or not state_draft.content_json:
        return None

    try:
        payload = json.loads(state_draft.content_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return GuidedChatStatePayload.model_validate(payload)


def save_guided_chat_state(db: Session, project_id: str, payload: GuidedChatStatePayload) -> GuidedChatStatePayload:
    serialized = payload.model_dump_json()
    state_draft = _get_state_draft(db, project_id)
    if state_draft is None:
        state_draft = Draft(
            project_id=project_id,
            title=GUIDED_CHAT_STATE_DRAFT_TITLE,
            content_markdown="# Guided chat state",
            content_json=serialized,
            status=DraftStatus.ARCHIVED.value,
        )
        db.add(state_draft)
    else:
        state_draft.content_json = serialized
        state_draft.status = DraftStatus.ARCHIVED.value
        db.add(state_draft)

    db.commit()
    return payload


def _get_state_draft(db: Session, project_id: str) -> Draft | None:
    stmt = (
        select(Draft)
        .where(
            Draft.project_id == project_id,
            Draft.title == GUIDED_CHAT_STATE_DRAFT_TITLE,
        )
        .order_by(Draft.updated_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
