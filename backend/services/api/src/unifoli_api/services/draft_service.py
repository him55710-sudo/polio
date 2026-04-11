from sqlalchemy import select
from sqlalchemy.orm import Session

from unifoli_api.db.models.draft import Draft
from unifoli_api.schemas.draft import DraftCreate, DraftUpdate


def create_draft(db: Session, project_id: str, payload: DraftCreate) -> Draft:
    draft = Draft(
        project_id=project_id,
        source_document_id=payload.source_document_id,
        title=payload.title,
        content_markdown=payload.content_markdown,
        content_json=payload.content_json,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def update_draft(db: Session, draft_id: str, payload: DraftUpdate) -> Draft | None:
    draft = get_draft(db, draft_id)
    if not draft:
        return None
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(draft, key, value)
    
    db.commit()
    db.refresh(draft)
    return draft


def list_drafts_for_project(db: Session, project_id: str) -> list[Draft]:
    stmt = (
        select(Draft)
        .where(Draft.project_id == project_id)
        .order_by(Draft.updated_at.desc())
    )
    return list(db.scalars(stmt))


def get_draft(db: Session, draft_id: str) -> Draft | None:
    return db.get(Draft, draft_id)
