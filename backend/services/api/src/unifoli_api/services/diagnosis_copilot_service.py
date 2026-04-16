from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from unifoli_api.db.models.diagnosis_run import DiagnosisRun
from unifoli_api.db.models.parsed_document import ParsedDocument
from unifoli_api.schemas.diagnosis import DiagnosisResultPayload
from unifoli_api.services.diagnosis_artifact_service import (
    build_diagnosis_copilot_brief as build_persisted_diagnosis_copilot_brief,
)


def _parse_result_payload(raw_payload: object) -> DiagnosisResultPayload | None:
    if raw_payload is None:
        return None
    try:
        if isinstance(raw_payload, str):
            return DiagnosisResultPayload.model_validate_json(raw_payload)
        if isinstance(raw_payload, dict):
            return DiagnosisResultPayload.model_validate(raw_payload)
    except Exception:  # noqa: BLE001
        return None
    return None


def _collect_canonical_lines(db: Session, *, project_id: str, max_items: int) -> list[str]:
    canonical_lines: list[str] = []
    documents = list(
        db.scalars(
            select(ParsedDocument)
            .where(
                ParsedDocument.project_id == project_id,
                ParsedDocument.status.in_(["parsed", "partial"]),
            )
            .order_by(ParsedDocument.updated_at.desc())
            .limit(2)
        )
    )
    for document in documents:
        metadata = getattr(document, "parse_metadata", None)
        if not isinstance(metadata, dict):
            continue
        canonical = metadata.get("student_record_canonical")
        if not isinstance(canonical, dict):
            continue
        for field, key in (
            ("timeline_signals", "signal"),
            ("major_alignment_hints", "hint"),
            ("weak_or_missing_sections", "section"),
            ("uncertainties", "message"),
        ):
            values = canonical.get(field)
            if not isinstance(values, list):
                continue
            for item in values[:max_items]:
                if not isinstance(item, dict):
                    continue
                value = str(item.get(key) or "").strip()
                if value:
                    canonical_lines.append(value)
        if len(canonical_lines) >= max_items * 3:
            break
    return canonical_lines[: max_items * 3]


def build_diagnosis_copilot_brief(
    db: Session,
    *,
    project_id: str | None,
    max_items: int = 4,
) -> str:
    if not project_id:
        return ""

    run = db.scalar(
        select(DiagnosisRun)
        .where(
            DiagnosisRun.project_id == project_id,
            DiagnosisRun.result_payload.is_not(None),
        )
        .order_by(DiagnosisRun.created_at.desc())
        .limit(1)
    )
    if run is None or not run.result_payload:
        return ""

    payload = _parse_result_payload(run.result_payload)
    if payload is None:
        return ""

    persisted_brief = build_persisted_diagnosis_copilot_brief(payload, max_items=max_items)
    if persisted_brief:
        return persisted_brief

    strengths = [item.strip() for item in payload.strengths[:max_items] if str(item).strip()]
    gaps = [item.strip() for item in payload.gaps[:max_items] if str(item).strip()]
    actions = [item.strip() for item in (payload.next_actions or [])[:max_items] if str(item).strip()]
    topics = [item.strip() for item in (payload.recommended_topics or [])[:max_items] if str(item).strip()]
    evidence_hooks = [
        f"{item.source_label} p.{item.page_number}" if item.page_number else item.source_label
        for item in (payload.citations or [])[:max_items]
        if item.source_label
    ]

    uncertainty_notes: list[str] = []
    if payload.document_quality and payload.document_quality.needs_review:
        uncertainty_notes.append(
            "Document extraction still needs manual review before making high-confidence claims."
        )
    if payload.fallback_used:
        uncertainty_notes.append(
            "Part of the diagnosis pipeline used deterministic fallback mode instead of the primary LLM path."
        )
    if not evidence_hooks:
        uncertainty_notes.append("Direct evidence hooks are sparse, so answers must stay conservative.")

    canonical_lines = _collect_canonical_lines(db, project_id=project_id, max_items=max_items)

    lines = [
        "[Diagnosis Copilot Brief]",
        f"- Headline: {payload.headline}",
        f"- Recommended focus: {payload.recommended_focus}",
    ]
    if strengths:
        lines.append("- Strengths: " + "; ".join(strengths))
    if gaps:
        lines.append("- Weaknesses: " + "; ".join(gaps))
    if actions:
        lines.append("- Next actions: " + "; ".join(actions))
    if topics:
        lines.append("- Recommended topics: " + "; ".join(topics))
    if evidence_hooks:
        lines.append("- Evidence hooks: " + "; ".join(evidence_hooks))
    if uncertainty_notes:
        lines.append("- Uncertainty notes: " + "; ".join(uncertainty_notes))
    if canonical_lines:
        lines.append("- Student record signals: " + "; ".join(canonical_lines))

    lines.extend(
        [
            "[Copilot Rules]",
            "- Answer from the persisted diagnosis result and student-record evidence first.",
            "- Do not imply guaranteed admissions or fabricate achievements that are not grounded.",
            "- If evidence is weak, say so plainly and turn the answer into the next safe action.",
        ]
    )
    return "\n".join(lines)
