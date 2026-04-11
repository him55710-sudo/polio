from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from unifoli_api.db.models.parsed_document import ParsedDocument
from unifoli_api.db.models.diagnosis_run import DiagnosisRun
from unifoli_api.schemas.diagnosis import DiagnosisResultPayload


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

    try:
        payload = DiagnosisResultPayload.model_validate_json(run.result_payload)
    except Exception:  # noqa: BLE001
        return ""

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
        uncertainty_notes.append("ë¬¸ì„œ ì¶”ì¶œ ? ë¢°?„ê? ??•„ ?¼ë? ?ë‹¨?€ ë³´ìˆ˜?ìœ¼ë¡??¤ë¤„????")
    if payload.fallback_used:
        uncertainty_notes.append("LLM ?´ë°± ëª¨ë“œê°€ ?¬ìš©?˜ì–´ ?¤ëª… ?˜ì????œí•œ?????ˆìŒ.")
    if not evidence_hooks:
        uncertainty_notes.append("ì§ì ‘ ?¸ìš© ê°€?¥í•œ ì¦ê±° ?…ì´ ë¶€ì¡±í•¨.")

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
    if canonical_lines:
        canonical_lines = canonical_lines[: max_items * 3]

    lines = [
        "[ì§„ë‹¨ ì½”íŒŒ?¼ëŸ¿ ë¸Œë¦¬??",
        f"- ì§„ë‹¨ ?¤ë“œ?¼ì¸: {payload.headline}",
        f"- ?µì‹¬ ì´ˆì : {payload.recommended_focus}",
    ]
    if strengths:
        lines.append("- ê°•ì : " + "; ".join(strengths))
    if gaps:
        lines.append("- ë³´ì™„?? " + "; ".join(gaps))
    if actions:
        lines.append("- ?¤ìŒ ?‰ë™: " + "; ".join(actions))
    if topics:
        lines.append("- ì¶”ì²œ ì£¼ì œ: " + "; ".join(topics))
    if evidence_hooks:
        lines.append("- ì¦ê±° ?? " + "; ".join(evidence_hooks))
    if uncertainty_notes:
        lines.append("- ë¶ˆí™•?¤ì„±: " + "; ".join(uncertainty_notes))
    if canonical_lines:
        lines.append("- ?™ìƒë¶€ êµ¬ì¡° ?œê·¸?? " + "; ".join(canonical_lines))

    lines.extend(
        [
            "[ì½”íŒŒ?¼ëŸ¿ ?‰ë™ ê·œì¹™]",
            "- ë°˜ë“œ???™ìƒ ê¸°ë¡/?…ë¡œ??ë¬¸ì„œ ê¸°ë°˜?¼ë¡œë§?ì¡°ì–¸?œë‹¤.",
            "- ?©ê²© ë³´ì¥, ?¸ë? ?±ê³¼ ?€ë¦¬ì‘?? ?ˆìœ„ ?œë™ ?œìˆ ??ê¸ˆì??œë‹¤.",
            "- ì§ì „ ?µë?ê³??œí˜„??ë°˜ë³µ?˜ë©´ ?™ì¼ ?˜ë?ë¥???êµ¬ì²´???¤ìŒ ?‰ë™?¼ë¡œ ë°”ê¿” ?œì•ˆ?œë‹¤.",
        ]
    )
    return "\n".join(lines)
