from __future__ import annotations

from typing import Any, Iterable


DIAGNOSIS_ARTIFACT_SCHEMA_VERSION = "2026-04-15-diagnosis-artifacts-v1"
_ARTIFACT_FIELDS = {
    "diagnosis_result_json",
    "diagnosis_report_markdown",
    "diagnosis_summary_json",
    "chatbot_context_json",
}


def _payload_dict(payload: Any, *, exclude_artifact_fields: bool = False) -> dict[str, Any]:
    if payload is None:
        return {}
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")
    elif isinstance(payload, dict):
        data = dict(payload)
    else:
        return {}
    if exclude_artifact_fields:
        for field_name in _ARTIFACT_FIELDS:
            data.pop(field_name, None)
    return data


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _string_list(values: Any, *, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = _normalize_text(raw)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _extract_labeled_list(values: Any, *, key: str, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            continue
        text = _normalize_text(item.get(key))
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _extend_unique(target: list[str], values: Iterable[str], *, limit: int) -> list[str]:
    seen = {item.lower() for item in target}
    for raw in values:
        text = _normalize_text(raw)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        target.append(text)
        if len(target) >= limit:
            break
    return target


def _collect_canonical_metadata(documents: list[Any]) -> dict[str, Any]:
    for document in documents:
        metadata = getattr(document, "parse_metadata", None)
        if not isinstance(metadata, dict):
            continue
        candidate = metadata.get("student_record_canonical")
        if isinstance(candidate, dict) and candidate:
            return candidate
    return {}


def _build_evidence_references(result_payload: dict[str, Any], *, limit: int = 8) -> list[dict[str, Any]]:
    citations = result_payload.get("citations")
    if not isinstance(citations, list):
        return []

    references: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None, str]] = set()
    for item in citations:
        if not isinstance(item, dict):
            continue
        source_label = _normalize_text(item.get("source_label"))
        excerpt = _normalize_text(item.get("excerpt"))
        if not source_label and not excerpt:
            continue
        page_number = item.get("page_number")
        if not isinstance(page_number, int):
            page_number = None
        key = (source_label, page_number, excerpt)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "source_label": source_label or "Document evidence",
                "section_label": _normalize_text(item.get("section_label")),
                "item_label": _normalize_text(item.get("item_label")),
                "page_number": page_number,
                "excerpt": excerpt,
                "relevance_score": float(item.get("relevance_score") or 0.0),
            }
        )
        if len(references) >= limit:
            break
    return references


def _build_summary_json(
    *,
    run_id: str,
    project_id: str,
    result_payload: dict[str, Any],
    evidence_references: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSIS_ARTIFACT_SCHEMA_VERSION,
        "diagnosis_run_id": run_id,
        "project_id": project_id,
        "headline": _normalize_text(result_payload.get("headline")),
        "overview": _normalize_text(result_payload.get("overview")) or None,
        "recommended_focus": _normalize_text(result_payload.get("recommended_focus")),
        "risk_level": _normalize_text(result_payload.get("risk_level")) or "warning",
        "strengths": _string_list(result_payload.get("strengths"), limit=6),
        "gaps": _string_list(result_payload.get("gaps"), limit=6),
        "next_actions": _string_list(result_payload.get("next_actions"), limit=6),
        "recommended_topics": _string_list(result_payload.get("recommended_topics"), limit=6),
        "fallback_used": bool(result_payload.get("fallback_used")),
        "fallback_reason": _normalize_text(result_payload.get("fallback_reason")) or None,
        "evidence_references": evidence_references,
    }


def _build_chatbot_context_json(
    *,
    run_id: str,
    project_id: str,
    result_payload: dict[str, Any],
    canonical_metadata: dict[str, Any],
    evidence_references: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_sections = _string_list(
        (canonical_metadata.get("section_coverage") or {}).get("missing_sections"),
        limit=6,
    )
    weak_sections = _extract_labeled_list(canonical_metadata.get("weak_or_missing_sections"), key="section", limit=6)
    target_risks = _string_list(result_payload.get("risks"), limit=6)
    if not target_risks:
        target_risks = _string_list(result_payload.get("gaps"), limit=6)

    caution_points: list[str] = []
    _extend_unique(caution_points, weak_sections, limit=8)
    _extend_unique(caution_points, missing_sections, limit=8)
    if bool(result_payload.get("fallback_used")):
        _extend_unique(
            caution_points,
            ["Deterministic fallback was used for part of the diagnosis pipeline."],
            limit=8,
        )
    document_quality = result_payload.get("document_quality")
    if isinstance(document_quality, dict) and bool(document_quality.get("needs_review")):
        _extend_unique(
            caution_points,
            ["The uploaded record still needs manual verification before making high-confidence claims."],
            limit=8,
        )

    return {
        "schema_version": DIAGNOSIS_ARTIFACT_SCHEMA_VERSION,
        "diagnosis_run_id": run_id,
        "project_id": project_id,
        "key_strengths": _string_list(result_payload.get("strengths"), limit=6),
        "key_weaknesses": _string_list(result_payload.get("gaps"), limit=6),
        "target_risks": target_risks,
        "recommended_activity_topics": _string_list(result_payload.get("recommended_topics"), limit=6),
        "caution_points": caution_points,
        "missing_sections": missing_sections,
        "major_alignment_hints": _extract_labeled_list(
            canonical_metadata.get("major_alignment_hints"),
            key="hint",
            limit=6,
        ),
        "timeline_signals": _extract_labeled_list(
            canonical_metadata.get("timeline_signals"),
            key="signal",
            limit=6,
        ),
        "evidence_references": evidence_references,
    }


def _build_report_markdown(
    *,
    summary_json: dict[str, Any],
    chatbot_context_json: dict[str, Any],
) -> str:
    lines = [
        "# Student Record Diagnosis",
        "",
        f"## Headline",
        summary_json.get("headline") or "Diagnosis summary unavailable",
        "",
        "## Recommended Focus",
        summary_json.get("recommended_focus") or "No recommended focus was generated.",
        "",
    ]

    overview = _normalize_text(summary_json.get("overview"))
    if overview:
        lines.extend(["## Overview", overview, ""])

    strengths = _string_list(summary_json.get("strengths"), limit=6)
    if strengths:
        lines.append("## Strengths")
        lines.extend(f"- {item}" for item in strengths)
        lines.append("")

    weaknesses = _string_list(chatbot_context_json.get("key_weaknesses"), limit=6)
    if weaknesses:
        lines.append("## Weaknesses")
        lines.extend(f"- {item}" for item in weaknesses)
        lines.append("")

    risks = _string_list(chatbot_context_json.get("target_risks"), limit=6)
    if risks:
        lines.append("## Target Risks")
        lines.extend(f"- {item}" for item in risks)
        lines.append("")

    actions = _string_list(summary_json.get("next_actions"), limit=6)
    if actions:
        lines.append("## Next Actions")
        lines.extend(f"- {item}" for item in actions)
        lines.append("")

    topics = _string_list(chatbot_context_json.get("recommended_activity_topics"), limit=6)
    if topics:
        lines.append("## Recommended Activity Topics")
        lines.extend(f"- {item}" for item in topics)
        lines.append("")

    cautions = _string_list(chatbot_context_json.get("caution_points"), limit=8)
    if cautions:
        lines.append("## Caution Points")
        lines.extend(f"- {item}" for item in cautions)
        lines.append("")

    evidence = chatbot_context_json.get("evidence_references")
    if isinstance(evidence, list) and evidence:
        lines.append("## Evidence References")
        for item in evidence[:8]:
            if not isinstance(item, dict):
                continue
            source_label = _normalize_text(item.get("source_label")) or "Document evidence"
            section_label = _normalize_text(item.get("section_label"))
            excerpt = _normalize_text(item.get("excerpt"))
            page_number = item.get("page_number")
            
            label_parts = []
            if section_label:
                label_parts.append(f"[{section_label}]")
            label_parts.append(source_label)
            full_label = " ".join(label_parts)
            
            page_suffix = f" (p.{page_number})" if isinstance(page_number, int) else ""
            if excerpt:
                lines.append(f"- {full_label}{page_suffix}: {excerpt}")
            else:
                lines.append(f"- {full_label}{page_suffix}")
        lines.append("")

    return "\n".join(lines).strip()


def build_diagnosis_artifact_bundle(
    *,
    run_id: str,
    project_id: str,
    result: Any,
    documents: list[Any],
) -> dict[str, Any]:
    result_payload = _payload_dict(result, exclude_artifact_fields=True)
    evidence_references = _build_evidence_references(result_payload)
    canonical_metadata = _collect_canonical_metadata(documents)
    summary_json = _build_summary_json(
        run_id=run_id,
        project_id=project_id,
        result_payload=result_payload,
        evidence_references=evidence_references,
    )
    chatbot_context_json = _build_chatbot_context_json(
        run_id=run_id,
        project_id=project_id,
        result_payload=result_payload,
        canonical_metadata=canonical_metadata,
        evidence_references=evidence_references,
    )
    report_markdown = _build_report_markdown(
        summary_json=summary_json,
        chatbot_context_json=chatbot_context_json,
    )
    return {
        "diagnosis_result_json": result_payload,
        "diagnosis_summary_json": summary_json,
        "diagnosis_report_markdown": report_markdown,
        "chatbot_context_json": chatbot_context_json,
    }


def build_diagnosis_copilot_brief(payload: Any, *, max_items: int = 4) -> str:
    data = _payload_dict(payload)
    if not data:
        return ""

    summary_json = data.get("diagnosis_summary_json")
    chatbot_context_json = data.get("chatbot_context_json")
    if not isinstance(summary_json, dict) or not isinstance(chatbot_context_json, dict):
        return ""

    headline = _normalize_text(summary_json.get("headline"))
    recommended_focus = _normalize_text(summary_json.get("recommended_focus"))
    strengths = _string_list(chatbot_context_json.get("key_strengths"), limit=max_items)
    weaknesses = _string_list(chatbot_context_json.get("key_weaknesses"), limit=max_items)
    risks = _string_list(chatbot_context_json.get("target_risks"), limit=max_items)
    topics = _string_list(chatbot_context_json.get("recommended_activity_topics"), limit=max_items)
    cautions = _string_list(chatbot_context_json.get("caution_points"), limit=max_items)

    evidence_lines: list[str] = []
    evidence_references = chatbot_context_json.get("evidence_references")
    if isinstance(evidence_references, list):
        for item in evidence_references[:max_items]:
            if not isinstance(item, dict):
                continue
            source_label = _normalize_text(item.get("source_label")) or "Document evidence"
            excerpt = _normalize_text(item.get("excerpt"))
            page_number = item.get("page_number")
            page_suffix = f" p.{page_number}" if isinstance(page_number, int) else ""
            evidence_lines.append(f"{source_label}{page_suffix}: {excerpt}" if excerpt else f"{source_label}{page_suffix}")

    lines = ["[Diagnosis Artifact Brief]"]
    if headline:
        lines.append(f"- Headline: {headline}")
    if recommended_focus:
        lines.append(f"- Recommended focus: {recommended_focus}")
    if strengths:
        lines.append("- Strengths: " + "; ".join(strengths))
    if weaknesses:
        lines.append("- Weaknesses: " + "; ".join(weaknesses))
    if risks:
        lines.append("- Target risks: " + "; ".join(risks))
    if topics:
        lines.append("- Recommended topics: " + "; ".join(topics))
    if cautions:
        lines.append("- Caution points: " + "; ".join(cautions))
    if evidence_lines:
        lines.append("- Evidence: " + "; ".join(evidence_lines))
    lines.extend(
        [
            "[Grounding Rules]",
            "- Answer from the persisted diagnosis artifact first.",
            "- Prefer evidence references over fresh speculation.",
            "- State uncertainty clearly when evidence is missing.",
        ]
    )
    return "\n".join(lines)


def extract_diagnosis_summary_text(payload: Any) -> str | None:
    data = _payload_dict(payload)
    summary_json = data.get("diagnosis_summary_json")
    if not isinstance(summary_json, dict):
        return None

    headline = _normalize_text(summary_json.get("headline"))
    recommended_focus = _normalize_text(summary_json.get("recommended_focus"))
    strengths = _string_list(summary_json.get("strengths"), limit=1)
    parts = [part for part in [headline, recommended_focus, *strengths] if part]
    if not parts:
        return None
    return " / ".join(parts[:3])
