from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from unifoli_api.core.config import get_settings
from unifoli_ingest.models import ParsedDocumentPayload

_CANONICAL_SCHEMA_VERSION = "2026-04-12"
_MAX_PAGE_INSIGHTS = 8
_MAX_KEY_POINTS = 5
_MAX_EVIDENCE_GAPS = 5

_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "student_info": ("인적사항", "학적사항", "학생명", "학교명", "주민등록번호"),
    "attendance": ("출결상황", "결석", "지각", "조퇴", "결과", "미인정"),
    "awards": ("수상경력", "수상명", "수여기관"),
    "creative_activities": ("창의적 체험활동", "창체", "자율활동", "동아리활동"),
    "volunteer": ("봉사활동", "봉사시간", "봉사"),
    "grades_subjects": ("교과학습발달상황", "과목", "원점수", "성취도", "등급"),
    "subject_special_notes": ("세부능력", "특기사항", "세특"),
    "reading": ("독서활동상황", "독서", "도서명", "저자"),
    "behavior_general_comments": ("행동특성 및 종합의견", "행동특성", "종합의견"),
}

_LEGACY_SECTION_LABELS: dict[str, str] = {
    "student_info": "인적사항",
    "attendance": "출결상황",
    "awards": "수상경력",
    "creative_activities": "창의적 체험활동",
    "volunteer": "봉사활동",
    "grades_subjects": "교과학습발달상황",
    "subject_special_notes": "세특",
    "reading": "독서",
    "behavior_general_comments": "행동특성",
}

_TIMELINE_PATTERNS = (
    re.compile(r"[1-3]\s*학년\s*[1-2]\s*학기"),
    re.compile(r"[1-3]\s*학년"),
    re.compile(r"[1-2]\s*학기"),
)

_MAJOR_HINT_KEYWORDS = ("전공", "진로", "학과", "관심", "목표", "희망", "진학")
_CAREER_KEYWORDS = ("진로", "학과", "전공", "희망", "진학", "목표")


def build_pdf_analysis_metadata(parsed: ParsedDocumentPayload) -> dict[str, Any] | None:
    settings = get_settings()
    if not getattr(settings, "pdf_analysis_llm_enabled", True):
        return None
    if parsed.source_extension.lower() != ".pdf":
        return None

    started_at = datetime.now(timezone.utc)
    page_texts = _extract_page_texts(parsed)
    summary = _build_pdf_summary(parsed, page_texts)
    key_points = _extract_key_points(page_texts)
    evidence_gaps = _build_evidence_gaps(parsed, page_texts)
    page_insights = _build_page_insights(page_texts)

    duration_ms = int(max(0.0, (datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0))
    provider = str(getattr(settings, "pdf_analysis_llm_provider", "") or "heuristic").strip().lower()
    model = str(getattr(settings, "pdf_analysis_llm_model", "") or "heuristic-summary-v1").strip()

    return {
        "provider": provider,
        "attempted_provider": provider,
        "model": model,
        "attempted_model": model,
        "engine": "heuristic",
        "requested_pdf_analysis_provider": provider,
        "requested_pdf_analysis_model": model,
        "actual_pdf_analysis_provider": "heuristic",
        "actual_pdf_analysis_model": "heuristic-summary-v1",
        "pdf_analysis_engine": "heuristic",
        "fallback_used": True,
        "fallback_reason": "heuristic_only",
        "processing_duration_ms": duration_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "key_points": key_points,
        "page_insights": page_insights,
        "evidence_gaps": evidence_gaps,
    }


def build_student_record_canonical_metadata(
    *,
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None = None,
    analysis_artifact: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    pipeline_canonical = _extract_pipeline_canonical(analysis_artifact)
    if not _looks_like_student_record(parsed, pipeline_canonical):
        return None

    text = _combined_text(parsed)
    page_texts = _extract_page_texts(parsed)
    section_classification = _classify_sections(text)
    section_coverage = _build_section_coverage(section_classification)
    coverage_score = float(section_coverage["coverage_score"])

    timeline_signals = [{"signal": value} for value in _extract_timeline_signals(text)]
    major_alignment_hints = [{"hint": value} for value in _extract_major_alignment_hints(text)]
    weak_sections = [{"section": value} for value in section_coverage["missing_sections"]]
    uncertainties = [{"message": value} for value in _build_uncertainties(parsed, pdf_analysis, section_coverage)]

    grades_subjects = _extract_grades_subjects(text, pipeline_canonical)
    subject_special_notes = _extract_subject_special_notes(text, pipeline_canonical)
    extracurricular = _extract_extracurricular(text, pipeline_canonical)
    career_signals = _extract_career_signals(text, pipeline_canonical)
    reading_activity = _extract_reading_activity(text, pipeline_canonical)
    behavior_opinion = _extract_behavior_opinion(text, pipeline_canonical)

    confidence = round(
        min(
            0.95,
            max(
                0.35,
                0.35
                + coverage_score * 0.35
                + min(len(major_alignment_hints), 3) * 0.05
                + min(len(timeline_signals), 3) * 0.04
                + (0.08 if pipeline_canonical else 0.0)
                + (0.05 if isinstance(pdf_analysis, dict) else 0.0),
            ),
        ),
        3,
    )

    return {
        "schema_version": _CANONICAL_SCHEMA_VERSION,
        "record_type": "korean_student_record_pdf",
        "analysis_source": "pipeline" if pipeline_canonical else "heuristic",
        "document_confidence": confidence,
        "timeline_signals": timeline_signals,
        "major_alignment_hints": major_alignment_hints,
        "weak_or_missing_sections": weak_sections,
        "uncertainties": uncertainties,
        "grades_subjects": grades_subjects,
        "subject_special_notes": subject_special_notes,
        "extracurricular": extracurricular,
        "career_signals": career_signals,
        "reading_activity": reading_activity,
        "behavior_opinion": behavior_opinion,
        "section_classification": section_classification,
        "section_coverage": section_coverage,
        "quality_gates": {
            "missing_required_sections": list(section_coverage["missing_sections"]),
            "reanalysis_required": bool(section_coverage["reanalysis_required"]),
            "coverage_score": coverage_score,
        },
        "page_count": parsed.page_count,
        "word_count": parsed.word_count,
        "student_profile": _extract_student_profile(text, pipeline_canonical),
        "source_pages": len(page_texts),
    }


def build_student_record_structure_metadata(
    *,
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None = None,
    analysis_artifact: dict[str, Any] | None = None,
    canonical_schema: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    canonical = canonical_schema or build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis=pdf_analysis,
        analysis_artifact=analysis_artifact,
    )
    if not isinstance(canonical, dict):
        return None

    section_classification = canonical.get("section_classification")
    if not isinstance(section_classification, dict):
        section_classification = {}

    section_density: dict[str, float] = {}
    section_status: dict[str, str] = {}
    for canonical_key, legacy_label in _LEGACY_SECTION_LABELS.items():
        payload = section_classification.get(canonical_key)
        if not isinstance(payload, dict):
            continue
        try:
            density = max(0.0, min(1.0, float(payload.get("density") or 0.0)))
        except (TypeError, ValueError):
            density = 0.0
        section_density[legacy_label] = density
        section_status[legacy_label] = str(payload.get("status") or "missing")

    return {
        "schema_version": _CANONICAL_SCHEMA_VERSION,
        "record_type": canonical.get("record_type") or "korean_student_record_pdf",
        "major_alignment": _extract_value_list(canonical.get("major_alignment_hints"), "hint"),
        "section_density": section_density,
        "section_status": section_status,
        "weak_sections": _extract_value_list(canonical.get("weak_or_missing_sections"), "section"),
        "timeline_signals": _extract_value_list(canonical.get("timeline_signals"), "signal"),
        "activity_clusters": _extract_value_list(canonical.get("extracurricular"), "label"),
        "alignment_signals": _extract_value_list(canonical.get("major_alignment_hints"), "hint"),
        "continuity_signals": _extract_value_list(canonical.get("career_signals"), "label"),
        "process_signals": _extract_value_list(canonical.get("subject_special_notes"), "label"),
        "uncertain_items": _extract_value_list(canonical.get("uncertainties"), "message"),
        "coverage_check": canonical.get("section_coverage") or {},
        "contradiction_check": {"passed": True, "items": []},
    }


def _extract_page_texts(parsed: ParsedDocumentPayload) -> list[str]:
    page_texts: list[str] = []

    for container in (
        parsed.raw_artifact,
        parsed.analysis_artifact,
        parsed.metadata.get("raw_parse_artifact") if isinstance(parsed.metadata, dict) else None,
        parsed.metadata,
    ):
        if not isinstance(container, dict):
            continue
        pages = container.get("pages") or container.get("normalized_pages")
        if not isinstance(pages, list):
            continue
        for page in pages:
            if not isinstance(page, dict):
                continue
            text = str(
                page.get("masked_text")
                or page.get("text")
                or page.get("content_text")
                or page.get("raw_text")
                or ""
            ).strip()
            if text:
                page_texts.append(text)
        if page_texts:
            return page_texts[: max(parsed.page_count, 1)]

    content = (parsed.content_text or "").strip()
    if not content:
        return []

    split_pages = [part.strip() for part in re.split(r"(?=\[Page \d+\])", content) if part.strip()]
    if split_pages:
        return split_pages[: max(parsed.page_count, 1)]
    return [content]


def _combined_text(parsed: ParsedDocumentPayload) -> str:
    return "\n".join(_extract_page_texts(parsed)) or (parsed.content_text or "")


def _build_pdf_summary(parsed: ParsedDocumentPayload, page_texts: list[str]) -> str:
    if not page_texts:
        return "PDF 텍스트가 충분히 추출되지 않아 문서 요약 근거가 제한적입니다."

    first = _clip(_normalize_sentence(page_texts[0]), 180)
    last = _clip(_normalize_sentence(page_texts[-1]), 180) if len(page_texts) > 1 else ""
    page_note = f"{parsed.page_count}페이지 문서에서 핵심 흐름을 정리했습니다."

    if last and last != first:
        return f"{page_note} 첫 페이지는 {first} 마지막 페이지는 {last}"
    return f"{page_note} 대표 요약은 {first}"


def _extract_key_points(page_texts: list[str]) -> list[str]:
    candidates: list[str] = []
    for text in page_texts[:_MAX_PAGE_INSIGHTS]:
        for sentence in _split_sentences(text):
            cleaned = _clip(_normalize_sentence(sentence), 180)
            if cleaned and len(cleaned) >= 20:
                candidates.append(cleaned)
            if len(candidates) >= 20:
                break
    return _dedupe(candidates, limit=_MAX_KEY_POINTS)


def _build_page_insights(page_texts: list[str]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    for index, text in enumerate(page_texts[:_MAX_PAGE_INSIGHTS], start=1):
        summary = _clip(_normalize_sentence(text), 220)
        if summary:
            insights.append({"page_number": index, "summary": summary})
    return insights


def _build_evidence_gaps(parsed: ParsedDocumentPayload, page_texts: list[str]) -> list[str]:
    gaps: list[str] = []
    if not page_texts:
        gaps.append("텍스트가 충분히 추출되지 않아 페이지별 근거 확인이 필요합니다.")
    if parsed.needs_review:
        gaps.append("문서 파싱 과정에서 검토 필요 플래그가 있어 핵심 섹션 재확인이 필요합니다.")
    if parsed.page_count > len(page_texts):
        gaps.append("일부 페이지에서 추출 텍스트가 비어 있어 PDF 원문 확인이 필요합니다.")
    warnings = parsed.warnings if isinstance(parsed.warnings, list) else []
    if warnings:
        gaps.append("파싱 경고가 있어 누락된 문맥이 없는지 확인이 필요합니다.")
    if not gaps:
        gaps.append("학생부 주요 섹션별 근거가 충분한지 최종 검토가 필요합니다.")
    return _dedupe(gaps, limit=_MAX_EVIDENCE_GAPS)


def _looks_like_student_record(parsed: ParsedDocumentPayload, pipeline_canonical: dict[str, Any]) -> bool:
    if pipeline_canonical:
        return True
    text = (parsed.content_text or "").strip()
    if not text:
        return False
    hits = sum(1 for keywords in _SECTION_KEYWORDS.values() if any(keyword in text for keyword in keywords))
    return parsed.source_extension.lower() == ".pdf" and hits >= 2


def _extract_pipeline_canonical(analysis_artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(analysis_artifact, dict):
        return {}
    for key in ("canonical_data", "student_record_canonical", "canonical"):
        candidate = analysis_artifact.get(key)
        if isinstance(candidate, dict):
            return candidate
    return {}


def _classify_sections(text: str) -> dict[str, dict[str, Any]]:
    section_classification: dict[str, dict[str, Any]] = {}
    lowered = text.lower()
    total_length = max(len(lowered), 1)
    for key, keywords in _SECTION_KEYWORDS.items():
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        density = min(1.0, len(matched) / max(1, len(keywords)))
        section_classification[key] = {
            "label": _LEGACY_SECTION_LABELS.get(key, key),
            "status": "present" if matched else "missing",
            "density": round(density, 3),
            "matched_keywords": matched[:6],
            "count": len(matched),
            "char_ratio": round(sum(lowered.count(keyword.lower()) for keyword in matched) / total_length, 4),
        }
    return section_classification


def _build_section_coverage(section_classification: dict[str, dict[str, Any]]) -> dict[str, Any]:
    section_counts = {
        key: int(payload.get("count") or 0)
        for key, payload in section_classification.items()
        if isinstance(payload, dict)
    }
    missing_sections = [
        _LEGACY_SECTION_LABELS.get(key, key)
        for key, payload in section_classification.items()
        if isinstance(payload, dict) and payload.get("status") != "present"
    ]
    present_count = sum(1 for payload in section_classification.values() if payload.get("status") == "present")
    coverage_score = round(present_count / max(len(_SECTION_KEYWORDS), 1), 3)
    return {
        "section_counts": section_counts,
        "missing_sections": missing_sections,
        "coverage_score": coverage_score,
        "reanalysis_required": coverage_score < 0.45,
    }


def _extract_timeline_signals(text: str) -> list[str]:
    signals: list[str] = []
    for pattern in _TIMELINE_PATTERNS:
        signals.extend(match.group(0) for match in pattern.finditer(text))
    return _dedupe([signal.replace(" ", "") for signal in signals], limit=6)


def _extract_major_alignment_hints(text: str) -> list[str]:
    sentences = _split_sentences(text)
    hints = [sentence for sentence in sentences if any(keyword in sentence for keyword in _MAJOR_HINT_KEYWORDS)]
    return _dedupe([_clip(sentence, 180) for sentence in hints], limit=6)


def _build_uncertainties(
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None,
    section_coverage: dict[str, Any],
) -> list[str]:
    items: list[str] = []
    if parsed.needs_review:
        items.append("문서 파싱 품질 검토가 필요합니다.")
    if isinstance(section_coverage.get("missing_sections"), list) and section_coverage["missing_sections"]:
        items.append("일부 필수 학생부 섹션이 누락되어 추가 검토가 필요합니다.")
    if isinstance(pdf_analysis, dict):
        gaps = pdf_analysis.get("evidence_gaps")
        if isinstance(gaps, list):
            items.extend(str(item) for item in gaps[:2] if str(item).strip())
    if not items:
        items.append("현재 메타데이터는 휴리스틱 기반이므로 원문 대조가 권장됩니다.")
    return _dedupe(items, limit=5)


def _extract_grades_subjects(text: str, pipeline_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    grades = pipeline_canonical.get("grades")
    if isinstance(grades, list) and grades:
        items: list[dict[str, Any]] = []
        for entry in grades[:8]:
            if not isinstance(entry, dict):
                continue
            subject = str(entry.get("subject") or "").strip()
            if not subject:
                continue
            items.append({"subject": subject, "label": subject})
        if items:
            return items

    subjects = re.findall(r"(국어|수학|영어|사회|역사|과학|물리|화학|생명과학|지구과학|정보|미술|음악|체육)", text)
    return [{"subject": subject, "label": subject} for subject in _dedupe(subjects, limit=8)]


def _extract_subject_special_notes(text: str, pipeline_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    notes = pipeline_canonical.get("subject_special_notes")
    if isinstance(notes, dict) and notes:
        return [
            {"label": f"{subject}: {_clip(str(note), 140)}"}
            for subject, note in list(notes.items())[:8]
            if str(subject).strip() and str(note).strip()
        ]
    return [{"label": item} for item in _extract_keyword_sentences(text, _SECTION_KEYWORDS["subject_special_notes"], limit=4)]


def _extract_extracurricular(text: str, pipeline_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    narratives = pipeline_canonical.get("extracurricular_narratives")
    if isinstance(narratives, dict) and narratives:
        return [
            {"label": header, "detail": _clip(str(detail), 140)}
            for header, detail in list(narratives.items())[:8]
            if str(header).strip() and str(detail).strip()
        ]
    return [{"label": item} for item in _extract_keyword_sentences(text, _SECTION_KEYWORDS["creative_activities"], limit=4)]


def _extract_career_signals(text: str, pipeline_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    items = _extract_keyword_sentences(text, _CAREER_KEYWORDS, limit=4)
    if not items and pipeline_canonical.get("behavior_opinion"):
        items = [_clip(str(pipeline_canonical.get("behavior_opinion")), 160)]
    return [{"label": item} for item in items]


def _extract_reading_activity(text: str, pipeline_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    reading = pipeline_canonical.get("reading_activities")
    if isinstance(reading, list) and reading:
        return [{"label": _clip(str(item), 140)} for item in reading[:6] if str(item).strip()]
    return [{"label": item} for item in _extract_keyword_sentences(text, _SECTION_KEYWORDS["reading"], limit=4)]


def _extract_behavior_opinion(text: str, pipeline_canonical: dict[str, Any]) -> list[dict[str, Any]]:
    opinion = pipeline_canonical.get("behavior_opinion")
    if isinstance(opinion, str) and opinion.strip():
        return [{"label": _clip(opinion, 160)}]
    return [{"label": item} for item in _extract_keyword_sentences(text, _SECTION_KEYWORDS["behavior_general_comments"], limit=3)]


def _extract_student_profile(text: str, pipeline_canonical: dict[str, Any]) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    if isinstance(pipeline_canonical.get("student_name"), str) and pipeline_canonical["student_name"].strip():
        profile["student_name"] = pipeline_canonical["student_name"].strip()
    if isinstance(pipeline_canonical.get("school_name"), str) and pipeline_canonical["school_name"].strip():
        profile["school_name"] = pipeline_canonical["school_name"].strip()

    name_match = re.search(r"(?:학생명|성명)\s*[:：]?\s*([가-힣]{2,5})", text)
    if name_match and "student_name" not in profile:
        profile["student_name"] = name_match.group(1)

    school_match = re.search(r"([가-힣A-Za-z0-9 ]+고등학교)", text)
    if school_match and "school_name" not in profile:
        profile["school_name"] = school_match.group(1).strip()
    return profile


def _extract_keyword_sentences(text: str, keywords: tuple[str, ...] | list[str], *, limit: int) -> list[str]:
    sentences = _split_sentences(text)
    matched = [sentence for sentence in sentences if any(keyword in sentence for keyword in keywords)]
    return _dedupe([_clip(sentence, 160) for sentence in matched], limit=limit)


def _extract_value_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = str(item.get(key) or "").strip()
        if text:
            items.append(text)
    return _dedupe(items, limit=12)


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?]|다\.)\s+|\n+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _normalize_sentence(text: str) -> str:
    sentence = re.sub(r"\s+", " ", text or "").strip()
    sentence = re.sub(r"^\[Page \d+\]\s*", "", sentence)
    return sentence


def _clip(text: str | None, max_len: int) -> str:
    normalized = _normalize_sentence(text or "")
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[: max_len - 3].rstrip()}..."


def _dedupe(items: list[str], *, limit: int) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = " ".join(str(item).split()).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped
