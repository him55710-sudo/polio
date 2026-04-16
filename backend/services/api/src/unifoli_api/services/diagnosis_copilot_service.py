# -*- coding: latin-1 -*-
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from unifoli_api.db.models.parsed_document import ParsedDocument
from unifoli_api.db.models.diagnosis_run import DiagnosisRun
from unifoli_api.schemas.diagnosis import DiagnosisResultPayload
from unifoli_api.services.diagnosis_artifact_service import (
    build_diagnosis_copilot_brief as build_persisted_diagnosis_copilot_brief,
)


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
        uncertainty_notes.append("문서 추출 ??뢰???? ???? ???? ??단?? 보수??으?????뤄????")
    if payload.fallback_used:
        uncertainty_notes.append("LLM ??백 모드가 ??용??어 ??명 ????????한??????음.")
    if not evidence_hooks:
        uncertainty_notes.append("직접 ??용 가??한 증거 ??이 부족함.")

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
        "[진단 코파??럿 브리??",
        f"- 진단 ??드??인: {payload.headline}",
        f"- ??심 초점: {payload.recommended_focus}",
    ]
    if strengths:
        lines.append("- 강점: " + "; ".join(strengths))
    if gaps:
        lines.append("- 보완?? " + "; ".join(gaps))
    if actions:
        lines.append("- ??음 ??동: " + "; ".join(actions))
    if topics:
        lines.append("- 추천 주제: " + "; ".join(topics))
    if evidence_hooks:
        lines.append("- 증거 ?? " + "; ".join(evidence_hooks))
    if uncertainty_notes:
        lines.append("- 불확??성: " + "; ".join(uncertainty_notes))
    if canonical_lines:
        lines.append("- ??생부 구조 ??그?? " + "; ".join(canonical_lines))

    lines.extend(
        [
            "[코파??럿 ??동 규칙]",
            "- 반드????생 기록/??로??문서 기반??로???조언??다.",
            "- ??격 보장, ???? ??과 ??리작?? ??위 ??동 ??술??금????다.",
            "- 직전 ?????????현??반복??면 ??일 ?????????구체????음 ??동??로 바꿔 ??안??다.",
        ]
    )
    return "\n".join(lines)
