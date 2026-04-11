from __future__ import annotations

import asyncio
import json
import re
import threading
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from unifoli_api.core.config import get_settings
from unifoli_api.core.llm import get_pdf_analysis_llm_client
from unifoli_api.core.security import sanitize_public_error
from unifoli_ingest.models import ParsedDocumentPayload

_MAX_PAGES_FOR_PROMPT = 8
_MAX_PAGE_TEXT_CHARS = 1400
_MAX_RAW_LLM_RESPONSE_CHARS = 16000
_PDF_ANALYSIS_FALLBACK_REASON = "LLM PDF analysis failed. Generated heuristic summary instead."
_CANONICAL_SCHEMA_VERSION = "2026-04-10"
_CANONICAL_MAX_ITEMS_PER_FIELD = 8
_CANONICAL_MAX_EVIDENCE_PER_ITEM = 3

_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "grades_subjects": ("êµê³¼?™ìŠµë°œë‹¬?í™©", "ê³¼ëª©", "?±ì·¨??, "?±ê¸‰", "?‰ê· ", "grades"),
    "subject_special_notes": ("?¸íŠ¹", "?¸ë??¥ë ¥", "?¹ê¸°?¬í•­", "subject_special_notes"),
    "extracurricular": ("ì°½ì˜??ì²´í—˜?œë™", "ì°½ì²´", "?™ì•„ë¦?, "ë´‰ì‚¬", "?ìœ¨?œë™", "ì§„ë¡œ?œë™"),
    "career_signals": ("ì§„ë¡œ", "ì§„í•™", "?¬ë§?™ê³¼", "?¬ë§ ?„ê³µ", "ëª©í‘œ", "career"),
    "reading_activity": ("?…ì„œ", "?„ì„œ", "?½ì?", "reading"),
    "behavior_opinion": ("?‰ë™?¹ì„±", "ì¢…í•©?˜ê²¬", "?¸ì„±", "?œë„", "behavior"),
}

_SUBJECT_KEYWORDS: tuple[str, ...] = (
    "êµ?–´",
    "?˜í•™",
    "?ì–´",
    "?œêµ­??,
    "?¬íšŒ",
    "??‚¬",
    "ê³¼í•™",
    "ë¬¼ë¦¬",
    "?”í•™",
    "?ëª…ê³¼í•™",
    "ì§€êµ¬ê³¼??,
    "?•ë³´",
    "ì»´í“¨??,
    "?„ë¡œê·¸ë˜ë°?,
    "ê¸°í•˜",
    "?•ë¥ ê³??µê³„",
    "ë¯¸ì ë¶?,
    "ê²½ì œ",
    "?•ì¹˜",
    "ë²?,
    "?¬ë¦¬",
    "ì² í•™",
    "ë¯¸ìˆ ",
    "?Œì•…",
    "ì²´ìœ¡",
)

_NORMALIZED_SECTION_ORDER: tuple[str, ...] = (
    "student_info",
    "attendance",
    "awards",
    "creative_activities",
    "volunteer",
    "grades_subjects",
    "subject_special_notes",
    "reading",
    "behavior_general_comments",
)

_NORMALIZED_SECTION_LABELS: dict[str, str] = {
    "student_info": "?¸ì ?¬í•­",
    "attendance": "ì¶œê²°?í™©",
    "awards": "?˜ìƒê²½ë ¥",
    "creative_activities": "ì°½ì˜??ì²´í—˜?œë™",
    "volunteer": "ë´‰ì‚¬?œë™",
    "grades_subjects": "êµê³¼?™ìŠµë°œë‹¬?í™©",
    "subject_special_notes": "?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­",
    "reading": "?…ì„œ?œë™?í™©",
    "behavior_general_comments": "?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬",
}

_NORMALIZED_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "student_info": ("?¸ì ?¬í•­", "?™ì ?¬í•­", "?±ëª…", "ì£¼ë??±ë¡ë²ˆí˜¸", "?™êµëª?, "?™ë…„"),
    "attendance": ("ì¶œê²°?í™©", "ê²°ì„", "ì§€ê°?, "ì¡°í‡´", "ê²°ê³¼", "ë¬´ë‹¨"),
    "awards": ("?˜ìƒê²½ë ¥", "?˜ìƒëª?, "?˜ì—¬ê¸°ê?", "?˜ìƒ?¼ì", "?˜ìƒ"),
    "creative_activities": ("ì°½ì˜??ì²´í—˜?œë™", "?ìœ¨?œë™", "?™ì•„ë¦¬í™œ??, "ì§„ë¡œ?œë™", "ì°½ì²´"),
    "volunteer": ("ë´‰ì‚¬?œë™", "ë´‰ì‚¬", "ë´‰ì‚¬?œê°„", "ë´‰ì‚¬?œë™ ?¤ì "),
    "grades_subjects": ("êµê³¼?™ìŠµë°œë‹¬?í™©", "?±ì·¨??, "?ì°¨", "ê³¼ëª©", "?ì ??, "?‰ê· "),
    "subject_special_notes": ("?¸ë??¥ë ¥", "?¹ê¸°?¬í•­", "?¸íŠ¹", "ê³¼ëª©ë³??¸ë??¥ë ¥"),
    "reading": ("?…ì„œ?œë™?í™©", "?…ì„œ", "?„ì„œëª?, "?€??),
    "behavior_general_comments": ("?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬", "?‰ë™?¹ì„±", "ì¢…í•©?˜ê²¬"),
}

_REQUIRED_NORMALIZED_SECTIONS: tuple[str, ...] = _NORMALIZED_SECTION_ORDER


class PdfPageInsight(BaseModel):
    page_number: int = Field(ge=1, le=5000)
    summary: str = Field(min_length=1, max_length=260)


class PdfAnalysisLLMResponse(BaseModel):
    summary: str = Field(min_length=1, max_length=900)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    page_insights: list[PdfPageInsight] = Field(default_factory=list, max_length=20)
    evidence_gaps: list[str] = Field(default_factory=list, max_length=8)


def build_pdf_analysis_metadata(parsed: ParsedDocumentPayload) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.pdf_analysis_llm_enabled:
        return None
    if parsed.source_extension.lower() != ".pdf":
        return None

    started_at = datetime.now(timezone.utc)
    page_items = _extract_page_items(parsed)
    heuristic = _build_heuristic_analysis(parsed=parsed, page_items=page_items)
    requested_model = _resolve_pdf_analysis_model_name()
    requested_provider = (settings.pdf_analysis_llm_provider or "ollama").strip().lower()

    def _base_metadata(
        *,
        engine: str,
        actual_provider: str,
        actual_model: str,
        fallback_used: bool,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        duration_ms = int(
            max(
                0.0,
                (datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0,
            )
        )
        payload: dict[str, Any] = {
            "provider": actual_provider,
            "model": actual_model,
            "engine": engine,
            "pdf_analysis_engine": engine,
            "generated_at": _utc_iso(),
            "requested_pdf_analysis_provider": requested_provider,
            "requested_pdf_analysis_model": requested_model,
            "actual_pdf_analysis_provider": actual_provider,
            "actual_pdf_analysis_model": actual_model,
            "fallback_used": fallback_used,
            "processing_duration_ms": duration_ms,
        }
        if fallback_reason:
            payload["fallback_reason"] = fallback_reason
        return payload

    if not page_items:
        return {
            **_base_metadata(
                engine="fallback",
                actual_provider="heuristic",
                actual_model="heuristic",
                fallback_used=True,
                fallback_reason="No extractable PDF page text was available for LLM analysis.",
            ),
            "attempted_provider": requested_provider,
            "attempted_model": requested_model,
            "failure_reason": "No extractable PDF page text was available for LLM analysis.",
            **heuristic,
        }

    llm = None
    prompt = _build_prompt(parsed=parsed, page_items=page_items)
    try:
        llm = get_pdf_analysis_llm_client()
        llm_response = _run_async(
            llm.generate_json(
                prompt=prompt,
                response_model=PdfAnalysisLLMResponse,
                system_instruction=_pdf_analysis_system_instruction(),
                temperature=0.15,
            )
        )
        normalized = _normalize_llm_response(llm_response=llm_response, heuristic=heuristic, page_items=page_items)
        return {
            **_base_metadata(
                engine="llm",
                actual_provider=requested_provider,
                actual_model=requested_model,
                fallback_used=False,
            ),
            **normalized,
        }
    except Exception as exc:
        failure_reason = sanitize_public_error(
            str(exc),
            fallback=_PDF_ANALYSIS_FALLBACK_REASON,
            max_length=220,
        )
        recovered = _recover_structured_response_from_text(
            llm=llm,
            prompt=prompt,
            heuristic=heuristic,
            page_items=page_items,
        )
        if recovered is not None:
            normalized = _normalize_llm_response(
                llm_response=recovered,
                heuristic=heuristic,
                page_items=page_items,
            )
            return {
                **_base_metadata(
                    engine="llm",
                    actual_provider=requested_provider,
                    actual_model=requested_model,
                    fallback_used=True,
                    fallback_reason="recovered_from_text_fallback",
                ),
                "attempted_provider": requested_provider,
                "attempted_model": requested_model,
                "recovered_from_text_fallback": True,
                **normalized,
            }
        return {
            **_base_metadata(
                engine="fallback",
                actual_provider="heuristic",
                actual_model="heuristic",
                fallback_used=True,
                fallback_reason=failure_reason,
            ),
            "attempted_provider": requested_provider,
            "attempted_model": requested_model,
            "failure_reason": failure_reason,
            **heuristic,
        }


def _run_async(coro):  # noqa: ANN001
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_holder: dict[str, Any] = {}
    error_holder: list[BaseException] = []

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result_holder["value"] = loop.run_until_complete(coro)
        except BaseException as exc:  # noqa: BLE001
            error_holder.append(exc)
        finally:
            loop.close()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if error_holder:
        raise error_holder[0]
    return result_holder.get("value")


def _pdf_analysis_system_instruction() -> str:
    return (
        "??• : ?™ìƒë¶€/?…ë¡œ??PDF???˜ì´ì§€ë³??µì‹¬ ?´ìš©???ˆì „?˜ê²Œ ?”ì•½?˜ëŠ” ë¶„ì„ ?„ìš°ë¯?\n"
        "ê·œì¹™:\n"
        "- ë°˜ë“œ???œêµ­??ì¡´ëŒ“ë§ë§Œ ?¬ìš©??ì£¼ì„¸??\n"
        "- ?œê³µ???ìŠ¤??ê·¼ê±° ë°–ì˜ ?¬ì‹¤??ë§Œë“¤ì§€ ë§ˆì„¸??\n"
        "- ê·¼ê±°ê°€ ë¶€ì¡±í•˜ë©?evidence_gaps??ëª…í™•???ì–´ ì£¼ì„¸??\n"
        "- ì¶œë ¥?€ ë°˜ë“œ??ì§€?•ëœ JSON ?¤í‚¤ë§ˆë? ?°ë¥´?¸ìš”.\n"
        "- summary??3~5ë¬¸ì¥, key_points??ìµœë? 5ê°? page_insights???˜ì´ì§€ë³???ì¤??”ì•½?¼ë¡œ ?‘ì„±??ì£¼ì„¸??\n"
    )


def _build_prompt(*, parsed: ParsedDocumentPayload, page_items: list[dict[str, Any]]) -> str:
    prompt_payload = {
        "page_count": parsed.page_count,
        "word_count": parsed.word_count,
        "parser_name": parsed.parser_name,
        "warnings": parsed.warnings[:5],
        "pages": page_items[:_MAX_PAGES_FOR_PROMPT],
    }
    return (
        "[?”ì²­]\n"
        "?…ë¡œ?œëœ PDF???˜ì´ì§€ë³??µì‹¬ê³??„ì²´ ë¬¸ì„œ ?ë¦„???”ì•½??ì£¼ì„¸??\n"
        "ê³¼ì¥/ì¶”ì¸¡ ?†ì´ ê·¼ê±° ê¸°ë°˜?¼ë¡œ ?‘ì„±??ì£¼ì„¸??\n\n"
        "[ë¬¸ì„œ ?°ì´??JSON]\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}\n"
    )


def _recover_structured_response_from_text(
    *,
    llm: Any,
    prompt: str,
    heuristic: dict[str, Any],
    page_items: list[dict[str, Any]],
) -> PdfAnalysisLLMResponse | None:
    if llm is None:
        return None
    try:
        raw_response = _run_async(_request_flexible_json_response(llm=llm, prompt=prompt))
    except Exception:
        return None
    return _parse_flexible_llm_response(raw=raw_response, heuristic=heuristic, page_items=page_items)


async def _request_flexible_json_response(*, llm: Any, prompt: str) -> str:
    fallback_prompt = (
        f"{prompt}\n"
        "[ì¶œë ¥ ?•ì‹]\n"
        "ë°˜ë“œ??JSON ê°ì²´ ?˜ë‚˜ë§?ì¶œë ¥??ì£¼ì„¸?? ë§ˆí¬?¤ìš´/?¤ëª…ë¬¸ì? ê¸ˆì??…ë‹ˆ??\n"
        "{\n"
        '  "summary": "ë¬¸ì„œ ?„ì²´ ?ë¦„ ?”ì•½ (ì¡´ëŒ“ë§?",\n'
        '  "key_points": ["?µì‹¬ ?¬ì¸??", "?µì‹¬ ?¬ì¸??"],\n'
        '  "page_insights": [{"page_number": 1, "summary": "1?˜ì´ì§€ ?µì‹¬"}],\n'
        '  "evidence_gaps": ["ê·¼ê±° ë¶€ì¡???ª©"]\n'
        "}\n"
    )
    chunks: list[str] = []
    total_chars = 0
    async for token in llm.stream_chat(
        prompt=fallback_prompt,
        system_instruction=_pdf_analysis_system_instruction(),
        temperature=0.1,
    ):
        if token:
            chunks.append(token)
            total_chars += len(token)
            if total_chars >= _MAX_RAW_LLM_RESPONSE_CHARS:
                break
    return "".join(chunks).strip()


def _parse_flexible_llm_response(
    *,
    raw: str,
    heuristic: dict[str, Any],
    page_items: list[dict[str, Any]],
) -> PdfAnalysisLLMResponse | None:
    if not raw:
        return None

    json_candidate = _extract_json_object_candidate(raw)
    if json_candidate:
        try:
            payload = json.loads(json_candidate)
            return _coerce_payload_to_response(
                payload=payload,
                heuristic=heuristic,
                page_items=page_items,
            )
        except Exception:
            pass

    freeform_response = _coerce_freeform_text_to_response(
        raw=raw,
        heuristic=heuristic,
        page_items=page_items,
    )
    return freeform_response


def _extract_json_object_candidate(raw: str) -> str | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    candidate = cleaned[start : end + 1].strip()
    try:
        json.loads(candidate)
    except Exception:
        return None
    return candidate


def _coerce_payload_to_response(
    *,
    payload: Any,
    heuristic: dict[str, Any],
    page_items: list[dict[str, Any]],
) -> PdfAnalysisLLMResponse:
    if not isinstance(payload, dict):
        raise ValueError("LLM JSON payload must be a dictionary.")

    allowed_pages = {int(item["page_number"]) for item in page_items if isinstance(item.get("page_number"), int)}
    summary = _clean_paragraph(str(payload.get("summary") or ""), max_len=900) or heuristic["summary"]

    key_points_raw = payload.get("key_points")
    key_points: list[str] = []
    if isinstance(key_points_raw, list):
        key_points = [_clean_line(str(item), max_len=180) for item in key_points_raw if str(item).strip()]
        key_points = [item for item in key_points if item][:5]
    if not key_points:
        key_points = heuristic["key_points"]

    evidence_raw = payload.get("evidence_gaps")
    evidence_gaps: list[str] = []
    if isinstance(evidence_raw, list):
        evidence_gaps = [_clean_line(str(item), max_len=180) for item in evidence_raw if str(item).strip()]
        evidence_gaps = [item for item in evidence_gaps if item][:5]
    if not evidence_gaps:
        evidence_gaps = heuristic["evidence_gaps"]

    normalized_page_insights: list[dict[str, Any]] = []
    page_insights_raw = payload.get("page_insights")
    if isinstance(page_insights_raw, list):
        for item in page_insights_raw:
            if not isinstance(item, dict):
                continue
            page_number = item.get("page_number")
            try:
                page_number_int = int(page_number)
            except (TypeError, ValueError):
                continue
            if page_number_int not in allowed_pages:
                continue
            summary_text = _clean_line(str(item.get("summary") or ""), max_len=260)
            if not summary_text:
                continue
            normalized_page_insights.append(
                {
                    "page_number": page_number_int,
                    "summary": summary_text,
                }
            )
            if len(normalized_page_insights) >= 8:
                break
    if not normalized_page_insights:
        normalized_page_insights = heuristic["page_insights"]

    return PdfAnalysisLLMResponse(
        summary=summary,
        key_points=key_points,
        page_insights=normalized_page_insights,
        evidence_gaps=evidence_gaps,
    )


def _coerce_freeform_text_to_response(
    *,
    raw: str,
    heuristic: dict[str, Any],
    page_items: list[dict[str, Any]],
) -> PdfAnalysisLLMResponse | None:
    normalized = raw.replace("\r\n", "\n").strip()
    if not normalized:
        return None
    normalized = re.sub(r"[*_`#>\-]{2,}", " ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    summary = _clean_paragraph(paragraphs[0] if paragraphs else "", max_len=900) or heuristic["summary"]

    line_items = [line.strip(" -*??t") for line in normalized.splitlines() if line.strip()]
    key_points: list[str] = []
    for line in line_items:
        if re.match(r"^\d+\.", line) or line.startswith("?µì‹¬") or line.startswith("?”ì•½"):
            cleaned = _clean_line(line, max_len=180)
            if cleaned:
                key_points.append(cleaned)
        if len(key_points) >= 5:
            break
    if not key_points:
        key_points = heuristic["key_points"]

    allowed_pages = {int(item["page_number"]) for item in page_items if isinstance(item.get("page_number"), int)}
    page_insights: list[dict[str, Any]] = []
    for line in line_items:
        match = re.search(r"(?P<page>\d{1,4})\s*?˜ì´ì§€\s*[:ï¼?]?\s*(?P<summary>.+)", line)
        if not match:
            continue
        page_number = int(match.group("page"))
        if page_number not in allowed_pages:
            continue
        page_summary = _clean_line(match.group("summary"), max_len=260)
        if not page_summary:
            continue
        page_insights.append({"page_number": page_number, "summary": page_summary})
        if len(page_insights) >= 8:
            break
    if not page_insights:
        page_insights = heuristic["page_insights"]

    evidence_gaps: list[str] = []
    for line in line_items:
        if any(keyword in line for keyword in ("ë¶€ì¡?, "?œê³„", "?•ì¸ ?„ìš”", "ê·¼ê±°", "?„ë½")):
            cleaned = _clean_line(line, max_len=180)
            if cleaned:
                evidence_gaps.append(cleaned)
        if len(evidence_gaps) >= 5:
            break
    if not evidence_gaps:
        evidence_gaps = heuristic["evidence_gaps"]

    return PdfAnalysisLLMResponse(
        summary=summary,
        key_points=key_points[:5],
        page_insights=page_insights[:8],
        evidence_gaps=evidence_gaps[:5],
    )


def _normalize_llm_response(
    *,
    llm_response: PdfAnalysisLLMResponse,
    heuristic: dict[str, Any],
    page_items: list[dict[str, Any]],
) -> dict[str, Any]:
    page_numbers = {item["page_number"] for item in page_items if isinstance(item.get("page_number"), int)}
    normalized_page_insights: list[dict[str, Any]] = []
    for item in llm_response.page_insights:
        if item.page_number not in page_numbers:
            continue
        summary = _clean_line(item.summary, max_len=260)
        if not summary:
            continue
        normalized_page_insights.append({"page_number": item.page_number, "summary": summary})
        if len(normalized_page_insights) >= 8:
            break

    if not normalized_page_insights:
        normalized_page_insights = heuristic["page_insights"]

    key_points = [_clean_line(line, max_len=180) for line in llm_response.key_points]
    key_points = [line for line in key_points if line][:5] or heuristic["key_points"]

    evidence_gaps = [_clean_line(line, max_len=180) for line in llm_response.evidence_gaps]
    evidence_gaps = [line for line in evidence_gaps if line][:5] or heuristic["evidence_gaps"]

    summary = _clean_paragraph(llm_response.summary, max_len=900) or heuristic["summary"]
    return {
        "summary": summary,
        "key_points": key_points,
        "page_insights": normalized_page_insights,
        "evidence_gaps": evidence_gaps,
    }


def _build_heuristic_analysis(*, parsed: ParsedDocumentPayload, page_items: list[dict[str, Any]]) -> dict[str, Any]:
    summary = (
        f"ì´?{parsed.page_count}?˜ì´ì§€, ??{parsed.word_count}?¨ì–´ê°€ ì¶”ì¶œ?˜ì—ˆ?µë‹ˆ?? "
        "ë¬¸ì„œ ?ë¦„?€ ?…ë¡œ?œëœ ?ë¬¸??ê¸°ì??¼ë¡œ ?•ë¦¬?˜ì—ˆ?¼ë©°, ?•ì¸???ìŠ¤??ë²”ìœ„ ?ˆì—?œë§Œ ë¶„ì„?ˆìŠµ?ˆë‹¤."
    )

    key_points = _extract_key_points(parsed.content_text)
    if not key_points:
        key_points = ["?µì‹¬ ë¬¸ì¥ ì¶”ì¶œ ê·¼ê±°ê°€ ë¶€ì¡±í•´ ì¶”ê? ?•ì¸???„ìš”?©ë‹ˆ??"]

    page_insights: list[dict[str, Any]] = []
    for item in page_items[:8]:
        snippet = _clean_line(str(item.get("snippet") or ""), max_len=220)
        if not snippet:
            snippet = "ì¶”ì¶œ ?ìŠ¤?¸ê? ì§§ì•„ ?µì‹¬ ?”ì•½ ê·¼ê±°ê°€ ?œí•œ?ì…?ˆë‹¤."
        page_insights.append({"page_number": int(item["page_number"]), "summary": snippet})

    evidence_gaps: list[str] = []
    if parsed.page_count == 0:
        evidence_gaps.append("?˜ì´ì§€ ì¶”ì¶œ ê²°ê³¼ê°€ ?†ì–´ ë¬¸ì„œ êµ¬ì¡°ë¥??ë‹¨?˜ê¸° ?´ë µ?µë‹ˆ??")
    if parsed.needs_review:
        evidence_gaps.append("?¼ë? ?˜ì´ì§€?ì„œ ì¶”ì¶œ ? ë¢°?„ê? ??•„ ?ë¬¸ ?•ì¸???„ìš”?©ë‹ˆ??")
    if parsed.warnings:
        evidence_gaps.append("?Œì‹± ê²½ê³ ê°€ ?ˆì–´ ?¼ë? ë¬¸ë§¥???„ë½?˜ì—ˆ?????ˆìŠµ?ˆë‹¤.")

    return {
        "summary": summary,
        "key_points": key_points[:5],
        "page_insights": page_insights,
        "evidence_gaps": evidence_gaps[:5],
    }


def _extract_page_items(parsed: ParsedDocumentPayload) -> list[dict[str, Any]]:
    pages = _extract_page_items_from_masked_or_raw_artifact(parsed)
    if pages:
        return pages

    pages = _extract_page_items_from_normalized_artifact(parsed)
    if pages:
        return pages

    return _extract_page_items_from_content_text(parsed)


def _extract_page_items_from_masked_or_raw_artifact(parsed: ParsedDocumentPayload) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    masked_pages = parsed.masked_artifact.get("pages") if isinstance(parsed.masked_artifact, dict) else None
    raw_pages = parsed.raw_artifact.get("pages") if isinstance(parsed.raw_artifact, dict) else None
    if isinstance(masked_pages, list):
        candidates.extend(item for item in masked_pages if isinstance(item, dict))
    elif isinstance(raw_pages, list):
        candidates.extend(item for item in raw_pages if isinstance(item, dict))

    for item in candidates:
        page_number = item.get("page_number")
        if not isinstance(page_number, int) or page_number <= 0:
            continue
        text = str(item.get("masked_text") or item.get("text") or "").strip()
        normalized_text = _normalize_page_text(text)
        if not normalized_text:
            continue
        pages.append(
            {
                "page_number": page_number,
                "text": normalized_text,
                "snippet": normalized_text[:180],
            }
        )
    return pages


def _extract_page_items_from_normalized_artifact(parsed: ParsedDocumentPayload) -> list[dict[str, Any]]:
    metadata = parsed.metadata if isinstance(parsed.metadata, dict) else {}
    normalized = metadata.get("normalized_artifact")
    if not isinstance(normalized, dict):
        return []

    page_descriptors = normalized.get("pages")
    elements = normalized.get("elements")
    if not isinstance(page_descriptors, list) or not isinstance(elements, list):
        return []

    element_text_by_id: dict[str, str] = {}
    element_texts_by_page: dict[int, list[str]] = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        page_number = element.get("page_number")
        if not isinstance(page_number, int) or page_number <= 0:
            continue
        text = _text_from_normalized_element(element)
        normalized_text = _normalize_page_text(text)
        if not normalized_text:
            continue
        element_id = str(element.get("element_id") or "").strip()
        if element_id:
            element_text_by_id[element_id] = normalized_text
        element_texts_by_page.setdefault(page_number, []).append(normalized_text)

    pages: list[dict[str, Any]] = []
    for descriptor in page_descriptors:
        if not isinstance(descriptor, dict):
            continue
        page_number = descriptor.get("page_number")
        if not isinstance(page_number, int) or page_number <= 0:
            continue

        fragments: list[str] = []
        element_ids = descriptor.get("element_ids")
        if isinstance(element_ids, list):
            for raw_id in element_ids:
                element_id = str(raw_id or "").strip()
                if not element_id:
                    continue
                text = element_text_by_id.get(element_id)
                if text:
                    fragments.append(text)
        if not fragments:
            fragments.extend(element_texts_by_page.get(page_number, []))

        merged = _normalize_page_text(" ".join(fragments))
        if not merged:
            continue
        pages.append(
            {
                "page_number": page_number,
                "text": merged,
                "snippet": merged[:180],
            }
        )

    return pages


def _extract_page_items_from_content_text(parsed: ParsedDocumentPayload) -> list[dict[str, Any]]:
    content_text = str(parsed.content_text or "").strip()
    if not content_text:
        return []

    segments = [segment.strip() for segment in re.split(r"(?=\[[^\]\n]{1,40}\])", content_text) if segment.strip()]
    if not segments:
        segments = [content_text]

    max_pages = max(int(parsed.page_count or 0), 1)
    normalized_segments: list[str] = []
    for segment in segments:
        normalized = _normalize_page_text(segment)
        if normalized:
            normalized_segments.append(normalized)
    if not normalized_segments:
        return []

    if len(normalized_segments) > max_pages:
        normalized_segments = normalized_segments[:max_pages]

    return [
        {
            "page_number": index + 1,
            "text": text,
            "snippet": text[:180],
        }
        for index, text in enumerate(normalized_segments)
    ]


def _text_from_normalized_element(element: dict[str, Any]) -> str:
    for key in ("masked_text", "raw_text", "text", "content"):
        value = element.get(key)
        if isinstance(value, str) and value.strip():
            return value

    rows = element.get("table_rows")
    if isinstance(rows, list):
        cell_texts: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            cells = row.get("cells")
            if not isinstance(cells, list):
                continue
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                text = str(cell.get("text") or "").strip()
                if text:
                    cell_texts.append(text)
        if cell_texts:
            return " | ".join(cell_texts)
    return ""


def _normalize_page_text(value: str | None) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    if not normalized:
        return ""
    return normalized[:_MAX_PAGE_TEXT_CHARS].strip()


def _extract_key_points(content_text: str) -> list[str]:
    lines = [line.strip() for line in re.split(r"[\n\.!?]", content_text) if line.strip()]
    dedup = OrderedDict()
    for line in lines:
        clean = _clean_line(line, max_len=180)
        if not clean:
            continue
        dedup.setdefault(clean, None)
        if len(dedup) >= 6:
            break
    return list(dedup.keys())[:5]


def _clean_line(value: str | None, *, max_len: int) -> str:
    if not value:
        return ""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[: max_len - 1].rstrip()}??


def _clean_paragraph(value: str | None, *, max_len: int) -> str:
    if not value:
        return ""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[: max_len - 1].rstrip()}??


def _resolve_pdf_analysis_model_name() -> str:
    settings = get_settings()
    provider = (settings.pdf_analysis_llm_provider or "ollama").strip().lower()
    if provider == "ollama":
        return settings.pdf_analysis_ollama_model or settings.ollama_model
    if provider == "gemini":
        return "gemini-1.5-pro"
    return provider or "unknown"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_student_record_canonical_metadata(
    *,
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None,
    analysis_artifact: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if parsed.source_extension.lower() != ".pdf":
        return None

    page_items = _extract_page_items(parsed)
    compact_text = re.sub(r"\s+", " ", (parsed.content_text or "").strip())
    pipeline_stages: list[dict[str, Any]] = []

    file_validation_ok = parsed.page_count >= 0 and parsed.word_count >= 0
    pipeline_stages.append(
        _build_stage_result(
            "file_validation",
            mode="deterministic_extraction",
            status="ok" if file_validation_ok else "failed",
            details={
                "source_extension": parsed.source_extension.lower(),
                "page_count": parsed.page_count,
                "word_count": parsed.word_count,
            },
        )
    )
    if not file_validation_ok:
        return {
            "schema_version": _CANONICAL_SCHEMA_VERSION,
            "record_type": "korean_student_record_pdf",
            "document_confidence": 0.0,
            "timeline_signals": [],
            "grades_subjects": [],
            "subject_special_notes": [],
            "extracurricular": [],
            "career_signals": [],
            "reading_activity": [],
            "behavior_opinion": [],
            "major_alignment_hints": [],
            "weak_or_missing_sections": [],
            "uncertainties": [
                {
                    "message": "ë¬¸ì„œ ê¸°ë³¸ ê²€ì¦??¨ê³„?ì„œ ?¤ë¥˜ê°€ ê°ì??˜ì—ˆ?µë‹ˆ??",
                    "related_field": "file_validation",
                    "confidence_impact": 1.0,
                    "evidence": [],
                }
            ],
            "normalized_sections": [],
            "section_coverage": {
                "section_counts": {section: 0 for section in _NORMALIZED_SECTION_ORDER},
                "found_sections": [],
                "missing_sections": list(_NORMALIZED_SECTION_ORDER),
                "coverage_score": 0.0,
                "reanalysis_required": True,
            },
            "evidence_bank": [],
            "quality_gates": {
                "required_sections_found": False,
                "missing_required_sections": list(_NORMALIZED_SECTION_ORDER),
                "reanalysis_required": True,
            },
            "pipeline_stages": pipeline_stages,
        }

    raw_chars = sum(len(str(item.get("text") or "")) for item in page_items)
    pipeline_stages.append(
        _build_stage_result(
            "raw_text_ocr_extraction",
            mode="deterministic_extraction",
            status="ok" if raw_chars > 0 else "degraded",
            details={
                "page_items": len(page_items),
                "extracted_chars": raw_chars,
                "parser_name": parsed.parser_name,
            },
        )
    )

    masked_pages = parsed.masked_artifact.get("pages") if isinstance(parsed.masked_artifact, dict) else None
    mask_applied = bool(parsed.masking_status == "masked" or isinstance(masked_pages, list))
    pipeline_stages.append(
        _build_stage_result(
            "masking_privacy_pass",
            mode="deterministic_extraction",
            status="ok" if mask_applied else "degraded",
            details={
                "masking_status": parsed.masking_status,
                "masked_page_count": len(masked_pages) if isinstance(masked_pages, list) else 0,
                "needs_review": bool(parsed.needs_review),
            },
        )
    )

    normalized_pages = _normalize_page_items(page_items)
    pipeline_stages.append(
        _build_stage_result(
            "page_normalization",
            mode="deterministic_extraction",
            status="ok" if normalized_pages else "degraded",
            details={
                "normalized_pages": len(normalized_pages),
                "normalized_characters": sum(int(item.get("char_count") or 0) for item in normalized_pages),
            },
        )
    )

    normalized_sections = _extract_normalized_sections(
        normalized_pages=normalized_pages,
        analysis_artifact=analysis_artifact,
        pdf_analysis=pdf_analysis,
    )
    section_coverage = _section_coverage_from_normalized(normalized_sections)
    evidence_bank = _build_evidence_bank(normalized_sections)
    pipeline_stages.append(
        _build_stage_result(
            "normalized_section_extraction",
            mode="deterministic_extraction",
            status="ok" if normalized_sections else "degraded",
            details={
                "normalized_section_entries": len(normalized_sections),
                "evidence_bank_entries": len(evidence_bank),
                "coverage_score": section_coverage.get("coverage_score", 0.0),
            },
        )
    )

    section_classification = _classify_record_sections(normalized_pages)
    present_sections = [
        section
        for section, payload in section_classification.items()
        if payload.get("status") == "present"
    ]
    pipeline_stages.append(
        _build_stage_result(
            "section_classification",
            mode="heuristic_inference",
            status="ok" if section_classification else "degraded",
            details={
                "present_sections": present_sections,
                "classified_section_count": len(section_classification),
            },
        )
    )

    timeline_signals = _extract_timeline_signals(normalized_pages)
    grades_subjects = _extract_grade_subject_signals(normalized_pages)
    subject_special_notes = _extract_section_items(
        normalized_pages=normalized_pages,
        section_key="subject_special_notes",
        label_prefix="?¸íŠ¹ ? í˜¸",
    )
    extracurricular = _extract_section_items(
        normalized_pages=normalized_pages,
        section_key="extracurricular",
        label_prefix="ì°½ì²´ ? í˜¸",
    )
    career_signals = _extract_section_items(
        normalized_pages=normalized_pages,
        section_key="career_signals",
        label_prefix="ì§„ë¡œ ? í˜¸",
    )
    reading_activity = _extract_section_items(
        normalized_pages=normalized_pages,
        section_key="reading_activity",
        label_prefix="?…ì„œ ? í˜¸",
    )
    behavior_opinion = _extract_section_items(
        normalized_pages=normalized_pages,
        section_key="behavior_opinion",
        label_prefix="?‰ë™?¹ì„± ? í˜¸",
    )
    major_alignment_hints = _extract_major_alignment_hints(normalized_pages)

    entity_count = (
        len(timeline_signals)
        + len(grades_subjects)
        + len(subject_special_notes)
        + len(extracurricular)
        + len(career_signals)
        + len(reading_activity)
        + len(behavior_opinion)
        + len(major_alignment_hints)
    )
    pipeline_stages.append(
        _build_stage_result(
            "entity_extraction",
            mode="heuristic_inference",
            status="ok" if entity_count > 0 else "degraded",
            details={
                "entity_count": entity_count,
                "timeline_signals": len(timeline_signals),
                "grades_subjects": len(grades_subjects),
                "major_alignment_hints": len(major_alignment_hints),
            },
        )
    )

    weak_or_missing_sections = _build_weak_or_missing_sections(
        section_classification=section_classification,
        normalized_pages=normalized_pages,
    )
    uncertainties = _build_canonical_uncertainties(
        parsed=parsed,
        pdf_analysis=pdf_analysis,
        section_classification=section_classification,
        weak_or_missing_sections=weak_or_missing_sections,
        normalized_pages=normalized_pages,
    )

    if isinstance(analysis_artifact, dict):
        _merge_analysis_artifact_into_canonical(
            analysis_artifact=analysis_artifact,
            normalized_pages=normalized_pages,
            grades_subjects=grades_subjects,
            subject_special_notes=subject_special_notes,
            extracurricular=extracurricular,
            reading_activity=reading_activity,
            behavior_opinion=behavior_opinion,
            uncertainties=uncertainties,
        )

    missing_required_sections = [
        _NORMALIZED_SECTION_LABELS.get(section, section)
        for section in section_coverage.get("missing_sections", [])
    ]
    if missing_required_sections:
        uncertainties.append(
            {
                "message": (
                    "?„ìˆ˜ ?¹ì…˜ ì¶”ì¶œ???„ì „?˜ì? ?Šì•„ ?¬ë¶„?ì´ ?„ìš”?©ë‹ˆ?? "
                    + ", ".join(missing_required_sections)
                ),
                "related_field": "section_coverage",
                "confidence_impact": 0.24,
                "evidence": _scope_evidence(normalized_pages),
            }
        )
    pipeline_stages.append(
        _build_stage_result(
            "section_coverage_check",
            mode="deterministic_extraction",
            status="failed" if missing_required_sections else "ok",
            details={
                "required_sections": list(_REQUIRED_NORMALIZED_SECTIONS),
                "missing_required_sections": section_coverage.get("missing_sections", []),
                "reanalysis_required": bool(section_coverage.get("reanalysis_required")),
            },
        )
    )

    pipeline_stages.append(
        _build_stage_result(
            "canonical_student_record_schema_generation",
            mode="deterministic_extraction",
            status="ok" if not missing_required_sections else "degraded",
            details={
                "schema_version": _CANONICAL_SCHEMA_VERSION,
                "required_field_count": 12,
            },
        )
    )

    evidence_link_count = _count_linked_evidence(
        timeline_signals=timeline_signals,
        grades_subjects=grades_subjects,
        subject_special_notes=subject_special_notes,
        extracurricular=extracurricular,
        career_signals=career_signals,
        reading_activity=reading_activity,
        behavior_opinion=behavior_opinion,
        major_alignment_hints=major_alignment_hints,
        weak_or_missing_sections=weak_or_missing_sections,
        uncertainties=uncertainties,
    )
    evidence_link_count += len(evidence_bank)
    pipeline_stages.append(
        _build_stage_result(
            "evidence_span_linking",
            mode="deterministic_extraction",
            status="ok" if evidence_link_count > 0 else "degraded",
            details={
                "linked_evidence_count": evidence_link_count,
            },
        )
    )

    document_confidence = _compute_document_confidence(
        parsed=parsed,
        pdf_analysis=pdf_analysis,
        entity_count=entity_count,
        weak_or_missing_sections=weak_or_missing_sections,
        uncertainties=uncertainties,
        normalized_pages=normalized_pages,
    )
    if section_coverage.get("reanalysis_required"):
        document_confidence = round(min(document_confidence, 0.49), 3)
    pipeline_stages.append(
        _build_stage_result(
            "uncertainty_confidence_scoring",
            mode="heuristic_inference",
            status="ok",
            details={
                "document_confidence": document_confidence,
                "uncertainty_count": len(uncertainties),
            },
        )
    )

    return {
        "schema_version": _CANONICAL_SCHEMA_VERSION,
        "record_type": "korean_student_record_pdf",
        "document_confidence": document_confidence,
        "timeline_signals": timeline_signals,
        "grades_subjects": grades_subjects,
        "subject_special_notes": subject_special_notes,
        "extracurricular": extracurricular,
        "career_signals": career_signals,
        "reading_activity": reading_activity,
        "behavior_opinion": behavior_opinion,
        "major_alignment_hints": major_alignment_hints,
        "weak_or_missing_sections": weak_or_missing_sections,
        "uncertainties": uncertainties,
        "normalized_sections": normalized_sections,
        "section_coverage": section_coverage,
        "evidence_bank": evidence_bank,
        "quality_gates": {
            "required_sections_found": not bool(section_coverage.get("missing_sections")),
            "missing_required_sections": section_coverage.get("missing_sections", []),
            "reanalysis_required": bool(section_coverage.get("reanalysis_required")),
        },
        "section_classification": section_classification,
        "pipeline_stages": pipeline_stages,
        "evidence_linked": evidence_link_count > 0,
    }


def _normalize_page_items(page_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for page in page_items:
        page_number = page.get("page_number")
        text = str(page.get("text") or "").strip()
        if not isinstance(page_number, int) or page_number <= 0 or not text:
            continue
        normalized_text = re.sub(r"\s+", " ", text).strip()
        if not normalized_text:
            continue
        normalized.append(
            {
                "page_number": page_number,
                "text": normalized_text,
                "char_count": len(normalized_text),
                "snippet": normalized_text[:180],
            }
        )
    return normalized


def _extract_normalized_sections(
    *,
    normalized_pages: list[dict[str, Any]],
    analysis_artifact: dict[str, Any] | None,
    pdf_analysis: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()

    for page in normalized_pages:
        page_number = int(page.get("page_number") or 0)
        text = str(page.get("text") or "")
        if page_number <= 0 or not text:
            continue
        lowered = text.lower()
        for section_id in _NORMALIZED_SECTION_ORDER:
            keywords = _NORMALIZED_SECTION_KEYWORDS.get(section_id, ())
            hit_keywords = [keyword for keyword in keywords if keyword.lower() in lowered][:2]
            if not hit_keywords:
                continue
            for hit_keyword in hit_keywords:
                match_index = lowered.find(hit_keyword.lower())
                start = max(0, match_index - 40)
                end = min(len(text), match_index + len(hit_keyword) + 130)
                quote = _clean_line(text[start:end], max_len=220)
                if not quote:
                    quote = _clean_line(text[:180], max_len=180)
                key = (page_number, section_id, quote)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    {
                        "page": page_number,
                        "section": section_id,
                        "section_name": _NORMALIZED_SECTION_LABELS.get(section_id, section_id),
                        "subsection": _infer_subsection_name(section_id=section_id, quote=quote, fallback=hit_keyword),
                        "raw_quote": quote,
                        "normalized_topic": _infer_activity_topic(quote=quote, section_id=section_id),
                        "confidence": 0.92,
                        "repair_source": "rule_based",
                    }
                )

    missing = _missing_required_sections(entries)
    if missing:
        entries.extend(
            _repair_missing_sections(
                missing_sections=missing,
                normalized_pages=normalized_pages,
                analysis_artifact=analysis_artifact,
                pdf_analysis=pdf_analysis,
            )
        )

    deduped: list[dict[str, Any]] = []
    seen_anchor: set[tuple[int, str]] = set()
    for item in sorted(entries, key=lambda x: (int(x.get("page") or 0), str(x.get("section") or ""))):
        page = int(item.get("page") or 0)
        section = str(item.get("section") or "").strip()
        if page <= 0 or not section:
            continue
        anchor = (page, section)
        if anchor in seen_anchor and str(item.get("repair_source") or "") == "llm_repair":
            continue
        seen_anchor.add(anchor)
        deduped.append(item)
    return deduped


def _repair_missing_sections(
    *,
    missing_sections: list[str],
    normalized_pages: list[dict[str, Any]],
    analysis_artifact: dict[str, Any] | None,
    pdf_analysis: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not missing_sections:
        return []

    repaired: list[dict[str, Any]] = []
    canonical_data = (
        analysis_artifact.get("canonical_data")
        if isinstance(analysis_artifact, dict) and isinstance(analysis_artifact.get("canonical_data"), dict)
        else {}
    )
    key_points = pdf_analysis.get("key_points") if isinstance(pdf_analysis, dict) and isinstance(pdf_analysis.get("key_points"), list) else []
    first_page = normalized_pages[0] if normalized_pages else {"page_number": 1, "text": ""}
    fallback_quote = _clean_line(str(first_page.get("text") or ""), max_len=180) or "?ë¬¸ ?¬ë¶„?ì´ ?„ìš”?©ë‹ˆ??"

    section_to_canonical_key: dict[str, str] = {
        "student_info": "student_name",
        "attendance": "attendance",
        "awards": "awards",
        "creative_activities": "extracurricular_narratives",
        "volunteer": "extracurricular_narratives",
        "grades_subjects": "grades",
        "subject_special_notes": "subject_special_notes",
        "reading": "reading_activities",
        "behavior_general_comments": "behavior_opinion",
    }

    for section_id in missing_sections:
        canonical_key = section_to_canonical_key.get(section_id, "")
        canonical_value = canonical_data.get(canonical_key) if isinstance(canonical_data, dict) and canonical_key else None
        llm_hint = next(
            (
                _clean_line(str(item), max_len=200)
                for item in key_points
                if isinstance(item, str)
                and any(keyword in item for keyword in _NORMALIZED_SECTION_KEYWORDS.get(section_id, ()))
            ),
            "",
        )
        if canonical_value in (None, "", [], {}) and not llm_hint:
            continue

        if llm_hint:
            quote = llm_hint
        elif isinstance(canonical_value, dict):
            quote = _clean_line(" ".join(str(value) for value in canonical_value.values()), max_len=200)
        elif isinstance(canonical_value, list):
            quote = _clean_line(" ".join(str(value) for value in canonical_value[:3]), max_len=200)
        else:
            quote = _clean_line(str(canonical_value), max_len=200)
        quote = quote or fallback_quote

        repaired.append(
            {
                "page": int(first_page.get("page_number") or 1),
                "section": section_id,
                "section_name": _NORMALIZED_SECTION_LABELS.get(section_id, section_id),
                "subsection": "LLM-repair",
                "raw_quote": quote,
                "normalized_topic": _infer_activity_topic(quote=quote, section_id=section_id),
                "confidence": 0.62,
                "repair_source": "llm_repair",
            }
        )
    return repaired


def _build_evidence_bank(normalized_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_bank: list[dict[str, Any]] = []
    for index, item in enumerate(normalized_sections, start=1):
        page = int(item.get("page") or 0)
        section_id = str(item.get("section") or "").strip()
        if page <= 0 or not section_id:
            continue
        quote = _clean_line(str(item.get("raw_quote") or ""), max_len=220)
        if not quote:
            continue
        confidence = float(item.get("confidence") or 0.0)
        major_relevance = _infer_major_relevance(quote)
        process_elements = _infer_process_elements(quote)
        evidence_bank.append(
            {
                "anchor_id": f"ev-{page:02d}-{section_id}-{index}",
                "page": page,
                "section": str(item.get("section_name") or section_id),
                "normalized_section": section_id,
                "theme": _infer_theme(quote),
                "subtheme": _infer_subtheme(quote),
                "quote": quote,
                "evidence_type": "direct" if str(item.get("repair_source") or "") == "rule_based" else "indirect",
                "major_relevance": major_relevance,
                "process_elements": process_elements,
                "confidence": round(max(0.0, min(1.0, confidence)), 3),
            }
        )
    return evidence_bank


def _section_coverage_from_normalized(normalized_sections: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    for item in normalized_sections:
        section = str(item.get("section") or "").strip()
        if section:
            counts[section] += 1
    found_sections = [section for section in _NORMALIZED_SECTION_ORDER if counts.get(section, 0) > 0]
    missing_sections = [section for section in _NORMALIZED_SECTION_ORDER if counts.get(section, 0) <= 0]
    coverage_score = round(len(found_sections) / max(len(_NORMALIZED_SECTION_ORDER), 1), 3)
    return {
        "section_counts": {section: int(counts.get(section, 0)) for section in _NORMALIZED_SECTION_ORDER},
        "found_sections": found_sections,
        "missing_sections": missing_sections,
        "coverage_score": coverage_score,
        "reanalysis_required": bool(missing_sections),
    }


def _missing_required_sections(normalized_sections: list[dict[str, Any]]) -> list[str]:
    present = {str(item.get("section") or "").strip() for item in normalized_sections}
    return [section for section in _REQUIRED_NORMALIZED_SECTIONS if section not in present]


def _infer_subsection_name(*, section_id: str, quote: str, fallback: str) -> str:
    if section_id == "creative_activities":
        for candidate in ("?ìœ¨?œë™", "?™ì•„ë¦¬í™œ??, "ì§„ë¡œ?œë™", "ë´‰ì‚¬?œë™"):
            if candidate in quote:
                return candidate
    if section_id == "subject_special_notes":
        subject_match = re.search(r"(êµ?–´|?˜í•™|?ì–´|ê³¼í•™|ë¬¼ë¦¬|?”í•™|?ëª…ê³¼í•™|ì§€êµ¬ê³¼???¬íšŒ|??‚¬|?•ë³´)", quote)
        if subject_match:
            return f"{subject_match.group(1)} ?¸íŠ¹"
    if section_id == "grades_subjects":
        subject_match = re.search(r"(êµ?–´|?˜í•™|?ì–´|ê³¼í•™|ë¬¼ë¦¬|?”í•™|?ëª…ê³¼í•™|ì§€êµ¬ê³¼???¬íšŒ|??‚¬|?•ë³´)", quote)
        if subject_match:
            return f"{subject_match.group(1)} ?±ì·¨"
    return fallback


def _infer_activity_topic(*, quote: str, section_id: str) -> str:
    if section_id in {"creative_activities", "volunteer"}:
        for keyword, topic in (
            ("ì§€?ê???, "ì§€?ê????¤ê³„"),
            ("ì¹œí™˜ê²?, "ì¹œí™˜ê²?ê±´ì¶•"),
            ("?¬ë‚œ", "?¬ë‚œ ?€??),
            ("ê¸°í›„", "ê¸°í›„ ?€??),
            ("ëª©ì¬", "ê±´ì¶• ?¬ë£Œ"),
            ("êµ¬ì¡°", "êµ¬ì¡° ?¤ê³„"),
            ("ê³µê°„", "ê³µê°„ ê¸°íš"),
        ):
            if keyword in quote:
                return topic
        return "ì°½ì²´ ?œë™"
    if section_id == "subject_special_notes":
        return "êµê³¼ ?¸ë? ?êµ¬"
    if section_id == "grades_subjects":
        return "êµê³¼ ?±ì·¨"
    if section_id == "reading":
        return "?…ì„œ ê¸°ë°˜ ?•ì¥"
    if section_id == "behavior_general_comments":
        return "?‰ë™?¹ì„±"
    return _NORMALIZED_SECTION_LABELS.get(section_id, section_id)


def _infer_major_relevance(quote: str) -> list[str]:
    mapping: tuple[tuple[str, str], ...] = (
        ("ê±´ì¶•", "ê±´ì¶•"),
        ("ê³µê°„", "ê³µê°„"),
        ("?¤ê³„", "?¤ê³„"),
        ("?¬ë£Œ", "?¬ë£Œ"),
        ("ëª©ì¬", "?¬ë£Œ"),
        ("êµ¬ì¡°", "êµ¬ì¡°"),
        ("ê¸°í›„", "?˜ê²½"),
        ("?˜ê²½", "?˜ê²½"),
        ("ì§€?ê???, "?˜ê²½"),
        ("?¬ë‚œ", "?¬ë‚œ ?€??),
        ("?„ì‹œ", "?„ì‹œ"),
        ("?¬ìš©??, "?¬ìš©??ê²½í—˜"),
    )
    relevance: list[str] = []
    for keyword, label in mapping:
        if keyword in quote and label not in relevance:
            relevance.append(label)
    return relevance[:4] or ["ê±´ì¶•"]


def _infer_process_elements(quote: str) -> dict[str, bool]:
    return {
        "motivation": any(keyword in quote for keyword in ("ê´€??, "?™ê¸°", "ë¬¸ì œ?˜ì‹", "ëª©í‘œ", "ê³„ê¸°")),
        "method": any(keyword in quote for keyword in ("?¤í—˜", "ë¶„ì„", "ì¡°ì‚¬", "?¤ê³„", "ëª¨í˜•", "ì¸¡ì •")),
        "finding": any(keyword in quote for keyword in ("ê²°ê³¼", "?•ì¸", "?„ì¶œ", "ë¹„êµ", "ë³€??, "?±ê³¼")),
        "limitation": any(keyword in quote for keyword in ("?œê³„", "?„ì‰¬?€", "?œì•½", "ë¶€ì¡?)),
        "extension": any(keyword in quote for keyword in ("?¬í™”", "?•ì¥", "?„ì†", "ê°œì„ ", "?ìš©")),
    }


def _infer_theme(quote: str) -> str:
    for keyword, theme in (
        ("ì§€?ê???, "ì§€?ê???ê±´ì¶•"),
        ("?¬ë‚œ", "?¬ë‚œ ?€??ê±´ì¶•"),
        ("ê¸°í›„", "ê¸°í›„ ?€??ê±´ì¶•"),
        ("ì¹œí™˜ê²?, "ì¹œí™˜ê²?ê±´ì¶•"),
        ("ëª©ì¬", "ê±´ì¶• ?¬ë£Œ"),
        ("êµ¬ì¡°", "êµ¬ì¡° ê³µí•™"),
        ("ê³µê°„", "ê³µê°„ ê¸°íš"),
    ):
        if keyword in quote:
            return theme
    return "ê±´ì¶• ?êµ¬"


def _infer_subtheme(quote: str) -> str:
    for keyword, label in (
        ("êµì°¨ ?ì¸µ ëª©ì¬", "êµì°¨ ?ì¸µ ëª©ì¬"),
        ("CLT", "êµì°¨ ?ì¸µ ëª©ì¬"),
        ("?´ì§„", "?´ì§„ êµ¬ì¡°"),
        ("?„ì†Œ", "?„ì†Œ ?€ê°?),
        ("?˜ê¸°", "?¨ì‹œë¸??˜ê¸°"),
        ("ì±„ê´‘", "ì±„ê´‘ ?¤ê³„"),
    ):
        if keyword in quote:
            return label
    return "?µì‹¬ ?œë™"


def _build_stage_result(
    stage_name: str,
    *,
    mode: str,
    status: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "stage": stage_name,
        "mode": mode,
        "status": status,
        "details": details,
    }


def _classify_record_sections(normalized_pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    total_pages = max(len(normalized_pages), 1)
    classification: dict[str, dict[str, Any]] = {}
    for section, keywords in _SECTION_KEYWORDS.items():
        matches: list[dict[str, Any]] = []
        keyword_hits = 0
        for page in normalized_pages:
            text = str(page.get("text") or "")
            page_hits = [keyword for keyword in keywords if keyword.lower() in text.lower()]
            if not page_hits:
                continue
            keyword_hits += len(page_hits)
            matches.append(
                {
                    "page_number": page["page_number"],
                    "keywords": page_hits[:4],
                    "excerpt": _clean_line(text, max_len=180),
                }
            )

        density = round(min(1.0, len(matches) / total_pages), 3)
        confidence = round(min(0.98, 0.35 + (density * 0.45) + min(keyword_hits, 6) * 0.04), 3)
        if density == 0.0:
            status = "missing"
        elif density < 0.25:
            status = "weak"
        else:
            status = "present"
        classification[section] = {
            "density": density,
            "confidence": confidence,
            "status": status,
            "matches": matches[:6],
        }
    return classification


def _extract_timeline_signals(normalized_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = (
        re.compile(r"\b[1-3]?™ë…„\s*[12]?™ê¸°\b"),
        re.compile(r"\b[1-3]?™ë…„\b"),
        re.compile(r"\b[12]?™ê¸°\b"),
        re.compile(r"\b20\d{2}\b"),
    )
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in normalized_pages:
        text = str(page.get("text") or "")
        for pattern in patterns:
            for match in pattern.finditer(text):
                signal = match.group(0).strip()
                if not signal or signal in seen:
                    continue
                seen.add(signal)
                entries.append(
                    {
                        "signal": signal,
                        "confidence": 0.86,
                        "source": "deterministic_pattern",
                        "evidence": [
                            _build_evidence(
                                page_number=int(page["page_number"]),
                                text=text,
                                start=match.start(),
                                end=match.end(),
                            )
                        ],
                    }
                )
                if len(entries) >= _CANONICAL_MAX_ITEMS_PER_FIELD:
                    return entries
    return entries


def _extract_grade_subject_signals(normalized_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    seen_subjects: set[str] = set()
    for subject in _SUBJECT_KEYWORDS:
        evidence = _find_keyword_evidence(
            normalized_pages=normalized_pages,
            keyword=subject,
            limit=_CANONICAL_MAX_EVIDENCE_PER_ITEM,
        )
        if not evidence or subject in seen_subjects:
            continue
        seen_subjects.add(subject)
        signals.append(
            {
                "subject": subject,
                "confidence": round(min(0.95, 0.58 + len(evidence) * 0.12), 3),
                "source": "deterministic_keyword",
                "evidence": evidence,
            }
        )
        if len(signals) >= _CANONICAL_MAX_ITEMS_PER_FIELD:
            break
    return signals


def _extract_section_items(
    *,
    normalized_pages: list[dict[str, Any]],
    section_key: str,
    label_prefix: str,
) -> list[dict[str, Any]]:
    keywords = _SECTION_KEYWORDS.get(section_key, ())
    if not keywords:
        return []
    items: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for keyword in keywords:
        evidence = _find_keyword_evidence(
            normalized_pages=normalized_pages,
            keyword=keyword,
            limit=_CANONICAL_MAX_EVIDENCE_PER_ITEM,
        )
        if not evidence:
            continue
        label = f"{label_prefix}:{keyword}"
        if label in seen_labels:
            continue
        seen_labels.add(label)
        items.append(
            {
                "label": label,
                "confidence": round(min(0.92, 0.55 + len(evidence) * 0.1), 3),
                "source": "deterministic_keyword",
                "evidence": evidence,
            }
        )
        if len(items) >= _CANONICAL_MAX_ITEMS_PER_FIELD:
            break
    return items


def _extract_major_alignment_hints(normalized_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    major_keywords = ("?„ê³µ", "ì§„ë¡œ", "?™ê³¼", "?¬ë§", "?í•©", "?°ê³„", "ëª©í‘œ")
    action_keywords = ("?êµ¬", "?¤í—˜", "?„ë¡œ?íŠ¸", "?œë™", "ë³´ê³ ??, "?¬í™”")
    hints: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for page in normalized_pages:
        text = str(page.get("text") or "")
        lowered = text.lower()
        if not any(keyword.lower() in lowered for keyword in major_keywords):
            continue
        if not any(keyword.lower() in lowered for keyword in action_keywords):
            continue
        signal = _clean_line(text, max_len=180)
        if not signal or signal in seen_labels:
            continue
        seen_labels.add(signal)
        evidence = _find_keyword_evidence(
            normalized_pages=[page],
            keyword="?„ê³µ" if "?„ê³µ" in text else "ì§„ë¡œ" if "ì§„ë¡œ" in text else "?™ê³¼",
            limit=1,
        )
        if not evidence:
            evidence = [
                _build_evidence(
                    page_number=int(page["page_number"]),
                    text=text,
                    start=0,
                    end=min(len(text), 50),
                )
            ]
        hints.append(
            {
                "hint": signal,
                "confidence": 0.72,
                "source": "heuristic_sentence_inference",
                "evidence": evidence,
            }
        )
        if len(hints) >= _CANONICAL_MAX_ITEMS_PER_FIELD:
            break
    return hints


def _build_weak_or_missing_sections(
    *,
    section_classification: dict[str, dict[str, Any]],
    normalized_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    weak_sections: list[dict[str, Any]] = []
    for section, payload in section_classification.items():
        status = str(payload.get("status") or "")
        if status not in {"weak", "missing"}:
            continue
        matches = payload.get("matches") if isinstance(payload.get("matches"), list) else []
        evidence: list[dict[str, Any]] = []
        for match in matches[:_CANONICAL_MAX_EVIDENCE_PER_ITEM]:
            page_number = match.get("page_number")
            excerpt = str(match.get("excerpt") or "").strip()
            if not isinstance(page_number, int) or page_number <= 0:
                continue
            if not excerpt:
                page = next((item for item in normalized_pages if item.get("page_number") == page_number), None)
                if isinstance(page, dict):
                    excerpt = str(page.get("snippet") or "")
            evidence.append(
                {
                    "page_number": page_number,
                    "excerpt": _clean_line(excerpt, max_len=220),
                    "start_char": 0,
                    "end_char": min(len(excerpt), 220),
                }
            )
        if not evidence and normalized_pages:
            page = normalized_pages[0]
            fallback_excerpt = str(page.get("snippet") or "?¹ì…˜ ê·¼ê±°ê°€ ë¶€ì¡±í•©?ˆë‹¤.")
            evidence = [
                {
                    "page_number": int(page["page_number"]),
                    "excerpt": _clean_line(fallback_excerpt, max_len=220),
                    "start_char": 0,
                    "end_char": min(len(fallback_excerpt), 220),
                }
            ]
        weak_sections.append(
            {
                "section": section,
                "status": status,
                "density": round(float(payload.get("density") or 0.0), 3),
                "confidence": round(float(payload.get("confidence") or 0.0), 3),
                "evidence": evidence,
            }
        )
    return weak_sections[:_CANONICAL_MAX_ITEMS_PER_FIELD]


def _build_canonical_uncertainties(
    *,
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None,
    section_classification: dict[str, dict[str, Any]],
    weak_or_missing_sections: list[dict[str, Any]],
    normalized_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    uncertainties: list[dict[str, Any]] = []
    if parsed.needs_review:
        uncertainties.append(
            {
                "message": "?Œì‹± ê²°ê³¼???˜ë™ ê²€???„ìš” ?Œë˜ê·¸ê? ?ˆìŠµ?ˆë‹¤.",
                "related_field": "document_confidence",
                "confidence_impact": 0.18,
                "evidence": _scope_evidence(normalized_pages),
            }
        )
    if parsed.parse_confidence < 0.6:
        uncertainties.append(
            {
                "message": "ë¬¸ì„œ ?Œì‹± confidenceê°€ ??•„ ?¼ë? ì¶”ë¡ ?€ ë³´ìˆ˜?ìœ¼ë¡??´ì„?´ì•¼ ?©ë‹ˆ??",
                "related_field": "document_confidence",
                "confidence_impact": 0.16,
                "evidence": _scope_evidence(normalized_pages),
            }
        )
    if pdf_analysis and pdf_analysis.get("engine") == "fallback":
        uncertainties.append(
            {
                "message": "PDF ë¶„ì„??LLM ?¤íŒ¨ ???´ë¦¬?¤í‹± fallback?¼ë¡œ ?ì„±?˜ì—ˆ?µë‹ˆ??",
                "related_field": "pdf_analysis",
                "confidence_impact": 0.12,
                "evidence": _scope_evidence(normalized_pages),
            }
        )
    for item in weak_or_missing_sections[:4]:
        section = str(item.get("section") or "").strip()
        status = str(item.get("status") or "").strip()
        if not section:
            continue
        uncertainties.append(
            {
                "message": f"{section} ?¹ì…˜??{status} ?íƒœë¡?ë¶„ë¥˜?˜ì—ˆ?µë‹ˆ??",
                "related_field": section,
                "confidence_impact": 0.08 if status == "weak" else 0.12,
                "evidence": item.get("evidence", [])[:_CANONICAL_MAX_EVIDENCE_PER_ITEM],
            }
        )
    for section, payload in section_classification.items():
        if payload.get("status") != "present":
            continue
        if float(payload.get("confidence") or 0.0) >= 0.55:
            continue
        uncertainties.append(
            {
                "message": f"{section} ë¶„ë¥˜ confidenceê°€ ??•„ ì¶”ê? ê²€ì¦ì´ ?„ìš”?©ë‹ˆ??",
                "related_field": section,
                "confidence_impact": 0.06,
                "evidence": _scope_evidence(normalized_pages),
            }
        )

    deduped: list[dict[str, Any]] = []
    seen_messages: set[str] = set()
    for item in uncertainties:
        message = str(item.get("message") or "").strip()
        if not message or message in seen_messages:
            continue
        seen_messages.add(message)
        deduped.append(item)
        if len(deduped) >= _CANONICAL_MAX_ITEMS_PER_FIELD:
            break
    return deduped


def _merge_analysis_artifact_into_canonical(
    *,
    analysis_artifact: dict[str, Any],
    normalized_pages: list[dict[str, Any]],
    grades_subjects: list[dict[str, Any]],
    subject_special_notes: list[dict[str, Any]],
    extracurricular: list[dict[str, Any]],
    reading_activity: list[dict[str, Any]],
    behavior_opinion: list[dict[str, Any]],
    uncertainties: list[dict[str, Any]],
) -> None:
    canonical_data = analysis_artifact.get("canonical_data")
    if not isinstance(canonical_data, dict):
        return

    def _append_if_evidenced(
        *,
        target: list[dict[str, Any]],
        label_key: str,
        label_value: str,
        source_text: str,
        confidence: float,
    ) -> None:
        evidence = _find_keyword_evidence(
            normalized_pages=normalized_pages,
            keyword=source_text,
            limit=_CANONICAL_MAX_EVIDENCE_PER_ITEM,
        )
        if not evidence:
            evidence = _find_keyword_evidence(
                normalized_pages=normalized_pages,
                keyword=label_value,
                limit=_CANONICAL_MAX_EVIDENCE_PER_ITEM,
            )
        if not evidence:
            uncertainties.append(
                {
                    "message": f"analysis_artifact??'{label_value}' ??ª©?€ ?˜ì´ì§€ ê·¼ê±° ë§í¬ë¥?ì°¾ì? ëª»í–ˆ?µë‹ˆ??",
                    "related_field": label_value,
                    "confidence_impact": 0.05,
                    "evidence": _scope_evidence(normalized_pages),
                }
            )
            return
        target.append(
            {
                label_key: label_value,
                "confidence": confidence,
                "source": "analysis_artifact_bridge",
                "evidence": evidence,
            }
        )

    for grade in canonical_data.get("grades", [])[:4]:
        if not isinstance(grade, dict):
            continue
        subject = str(grade.get("subject") or "").strip()
        if not subject:
            continue
        _append_if_evidenced(
            target=grades_subjects,
            label_key="subject",
            label_value=subject,
            source_text=subject,
            confidence=0.74,
        )

    subject_notes = canonical_data.get("subject_special_notes")
    if isinstance(subject_notes, dict):
        for subject, note in list(subject_notes.items())[:4]:
            subject_text = str(subject or "").strip()
            note_text = str(note or "").strip()
            if not subject_text and not note_text:
                continue
            _append_if_evidenced(
                target=subject_special_notes,
                label_key="label",
                label_value=f"?¸íŠ¹:{subject_text or 'ë¯¸ìƒ ê³¼ëª©'}",
                source_text=note_text or subject_text,
                confidence=0.71,
            )

    extracurricular_map = canonical_data.get("extracurricular_narratives")
    if isinstance(extracurricular_map, dict):
        for name, narrative in list(extracurricular_map.items())[:4]:
            name_text = str(name or "").strip()
            narrative_text = str(narrative or "").strip()
            if not name_text and not narrative_text:
                continue
            _append_if_evidenced(
                target=extracurricular,
                label_key="label",
                label_value=f"ì°½ì²´:{name_text or 'ë¯¸ìƒ ?ì—­'}",
                source_text=narrative_text or name_text,
                confidence=0.69,
            )

    for reading_item in canonical_data.get("reading_activities", [])[:4]:
        reading_text = str(reading_item or "").strip()
        if not reading_text:
            continue
        _append_if_evidenced(
            target=reading_activity,
            label_key="label",
            label_value="?…ì„œ?œë™",
            source_text=reading_text,
            confidence=0.66,
        )

    behavior_text = str(canonical_data.get("behavior_opinion") or "").strip()
    if behavior_text:
        _append_if_evidenced(
            target=behavior_opinion,
            label_key="label",
            label_value="?‰ë™?¹ì„±/ì¢…í•©?˜ê²¬",
            source_text=behavior_text,
            confidence=0.68,
        )


def _count_linked_evidence(**fields: list[dict[str, Any]]) -> int:
    linked = 0
    for items in fields.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            evidence = item.get("evidence")
            if isinstance(evidence, list):
                linked += len(evidence)
    return linked


def _compute_document_confidence(
    *,
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None,
    entity_count: int,
    weak_or_missing_sections: list[dict[str, Any]],
    uncertainties: list[dict[str, Any]],
    normalized_pages: list[dict[str, Any]],
) -> float:
    base = 0.28
    base += min(0.32, max(0.0, float(parsed.parse_confidence)) * 0.32)
    base += min(0.16, len(normalized_pages) * 0.03)
    base += min(0.16, entity_count * 0.012)
    if pdf_analysis and pdf_analysis.get("engine") == "llm":
        base += 0.04
    if pdf_analysis and pdf_analysis.get("engine") == "fallback":
        base -= 0.06
    base -= min(0.2, len(weak_or_missing_sections) * 0.03)
    base -= min(0.22, len(uncertainties) * 0.035)
    if parsed.needs_review:
        base -= 0.08
    return round(max(0.05, min(0.98, base)), 3)


def _find_keyword_evidence(
    *,
    normalized_pages: list[dict[str, Any]],
    keyword: str,
    limit: int,
) -> list[dict[str, Any]]:
    normalized_keyword = str(keyword or "").strip()
    if not normalized_keyword:
        return []
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for page in normalized_pages:
        text = str(page.get("text") or "")
        if not text:
            continue
        lowered = text.lower()
        lowered_keyword = normalized_keyword.lower()
        start = lowered.find(lowered_keyword)
        while start != -1:
            key = (int(page["page_number"]), start)
            if key not in seen:
                seen.add(key)
                end = start + len(normalized_keyword)
                evidence.append(
                    _build_evidence(
                        page_number=int(page["page_number"]),
                        text=text,
                        start=start,
                        end=end,
                    )
                )
                if len(evidence) >= limit:
                    return evidence
            start = lowered.find(lowered_keyword, start + len(lowered_keyword))
    return evidence


def _build_evidence(*, page_number: int, text: str, start: int, end: int) -> dict[str, Any]:
    excerpt_start = max(0, start - 45)
    excerpt_end = min(len(text), end + 95)
    excerpt = _clean_line(text[excerpt_start:excerpt_end], max_len=220)
    return {
        "page_number": page_number,
        "excerpt": excerpt,
        "start_char": max(0, start),
        "end_char": min(len(text), max(end, start + 1)),
    }


def _scope_evidence(normalized_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for page in normalized_pages[:2]:
        snippet = str(page.get("snippet") or "").strip()
        if not snippet:
            continue
        evidence.append(
            {
                "page_number": int(page["page_number"]),
                "excerpt": _clean_line(snippet, max_len=220),
                "start_char": 0,
                "end_char": min(len(snippet), 220),
            }
        )
    return evidence


def build_student_record_structure_metadata(
    *,
    parsed: ParsedDocumentPayload,
    pdf_analysis: dict[str, Any] | None,
    analysis_artifact: dict[str, Any] | None = None,
    canonical_schema: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if parsed.source_extension.lower() != ".pdf":
        return None

    page_items = _extract_page_items(parsed)
    page_count = max(parsed.page_count, len(page_items), 1)
    full_text = (parsed.content_text or "").strip()
    compact_text = re.sub(r"\s+", " ", full_text)
    resolved_canonical = (
        canonical_schema
        if isinstance(canonical_schema, dict)
        else build_student_record_canonical_metadata(
            parsed=parsed,
            pdf_analysis=pdf_analysis,
            analysis_artifact=analysis_artifact,
        )
    )
    canonical_section_density = _legacy_section_density_from_canonical(resolved_canonical)
    normalized_sections = (
        resolved_canonical.get("normalized_sections")
        if isinstance(resolved_canonical, dict) and isinstance(resolved_canonical.get("normalized_sections"), list)
        else []
    )
    section_coverage = (
        resolved_canonical.get("section_coverage")
        if isinstance(resolved_canonical, dict) and isinstance(resolved_canonical.get("section_coverage"), dict)
        else _section_coverage_from_normalized(normalized_sections)
    )

    section_keywords: dict[str, tuple[str, ...]] = {
        "?¸íŠ¹": ("?¸ë??¥ë ¥", "?¹ê¸°?¬í•­", "êµê³¼?™ìŠµë°œë‹¬?í™©", "subject_special_notes"),
        "ì°½ì²´": ("ì°½ì˜??ì²´í—˜?œë™", "?™ì•„ë¦?, "ë´‰ì‚¬", "?ìœ¨?œë™", "extracurricular"),
        "ì§„ë¡œ": ("ì§„ë¡œ", "ì§„í•™", "?¬ë§?™ê³¼", "career"),
        "?‰ë™?¹ì„±": ("?‰ë™?¹ì„±", "ì¢…í•©?˜ê²¬", "behavior"),
        "êµê³¼?™ìŠµë°œë‹¬?í™©": ("êµê³¼?™ìŠµë°œë‹¬?í™©", "?±ì·¨??, "ê³¼ëª©", "grades"),
        "?…ì„œ": ("?…ì„œ", "reading"),
    }

    section_hits: dict[str, int] = {}
    for section, keywords in section_keywords.items():
        hits = 0
        for page in page_items:
            text = str(page.get("text") or "").lower()
            if any(keyword.lower() in text for keyword in keywords):
                hits += 1
        if hits == 0 and compact_text:
            lowered = compact_text.lower()
            if any(keyword.lower() in lowered for keyword in keywords):
                hits = 1
        section_hits[section] = hits

    max_hits = max(section_hits.values()) if section_hits else 1
    section_density = {
        key: round(min(1.0, (value / max_hits) if max_hits else 0.0), 3)
        for key, value in section_hits.items()
    }
    normalized_to_legacy = {
        "student_info": "?¸ì ?¬í•­",
        "attendance": "ì¶œê²°?í™©",
        "awards": "?˜ìƒê²½ë ¥",
        "creative_activities": "ì°½ì²´",
        "volunteer": "ì°½ì²´",
        "grades_subjects": "êµê³¼?™ìŠµë°œë‹¬?í™©",
        "subject_special_notes": "?¸íŠ¹",
        "reading": "?…ì„œ",
        "behavior_general_comments": "?‰ë™?¹ì„±",
    }
    coverage_counts = section_coverage.get("section_counts", {}) if isinstance(section_coverage, dict) else {}
    if isinstance(coverage_counts, dict):
        for section_id, count in coverage_counts.items():
            legacy = normalized_to_legacy.get(str(section_id))
            if not legacy:
                continue
            normalized_score = max(0.0, min(1.0, float(count) / max(page_count, 1)))
            section_density[legacy] = max(section_density.get(legacy, 0.0), round(normalized_score, 3))
    for section, density in canonical_section_density.items():
        section_density[section] = max(section_density.get(section, 0.0), density)

    weak_sections = [
        section
        for section, density in section_density.items()
        if density <= 0.2
    ]

    timeline_patterns = (
        r"\b[1-3]?™ë…„\b",
        r"\b[12]?™ê¸°\b",
        r"\b20\d{2}\b",
    )
    timeline_signals = []
    for pattern in timeline_patterns:
        for match in re.findall(pattern, compact_text):
            timeline_signals.append(str(match))
    timeline_signals.extend(_extract_canonical_string_values(resolved_canonical, "timeline_signals", "signal"))
    timeline_signals = _dedupe_list(timeline_signals, limit=10)

    activity_clusters = _extract_cluster_hints(compact_text)
    alignment_signals = _extract_alignment_hints(compact_text)
    alignment_signals.extend(_extract_canonical_string_values(resolved_canonical, "major_alignment_hints", "hint"))
    continuity_signals = _extract_keyword_sentences(
        compact_text,
        keywords=("?¬í™”", "?•ì¥", "?„ì†", "ë¹„êµ", "?°ê³„", "ì§€??),
        limit=5,
    )
    process_reflection_signals = _extract_keyword_sentences(
        compact_text,
        keywords=("ê³¼ì •", "ë°©ë²•", "?œê³„", "ê°œì„ ", "?±ì°°", "?¼ë“œë°?),
        limit=5,
    )

    uncertain_items: list[str] = []
    if parsed.needs_review:
        uncertain_items.append("?Œì‹± ?ˆì§ˆ ê²½ê³ ê°€ ?ˆì–´ ?¼ë? ?¹ì…˜ ë¶„ë¥˜ ?•í™•?„ê? ??„ ???ˆìŠµ?ˆë‹¤.")
    if page_count <= 1:
        uncertain_items.append("?˜ì´ì§€ ?˜ê? ë§¤ìš° ?ì–´ ?™ê¸°/?°ì†??ì¶”ì •??? ë¢°?„ê? ??Šµ?ˆë‹¤.")
    if not compact_text:
        uncertain_items.append("ì¶”ì¶œ ?ìŠ¤?¸ê? ë¶€ì¡±í•´ êµ¬ì¡° ì¶”ì •???œí•œ?˜ì—ˆ?µë‹ˆ??")
    if pdf_analysis and pdf_analysis.get("engine") == "fallback":
        uncertain_items.append("PDF ?”ì•½??heuristic fallback?¼ë¡œ ?ì„±?˜ì—ˆ?µë‹ˆ??")

    if isinstance(resolved_canonical, dict):
        weak_sections.extend(_extract_canonical_string_values(resolved_canonical, "weak_or_missing_sections", "section"))
        uncertain_items.extend(_extract_canonical_string_values(resolved_canonical, "uncertainties", "message"))
        gates = resolved_canonical.get("quality_gates")
        if isinstance(gates, dict):
            for section_id in gates.get("missing_required_sections", []) if isinstance(gates.get("missing_required_sections"), list) else []:
                label = _NORMALIZED_SECTION_LABELS.get(str(section_id), str(section_id))
                if label:
                    weak_sections.append(label)
            if gates.get("reanalysis_required"):
                uncertain_items.append("?„ìˆ˜ ?¹ì…˜ ì¶”ì¶œ ?„ë½?¼ë¡œ ?¬ë¶„?ì´ ?„ìš”?©ë‹ˆ??")

    if isinstance(analysis_artifact, dict):
        canonical_data = analysis_artifact.get("canonical_data")
        if isinstance(canonical_data, dict):
            if canonical_data.get("grades"):
                section_density["êµê³¼?™ìŠµë°œë‹¬?í™©"] = max(section_density.get("êµê³¼?™ìŠµë°œë‹¬?í™©", 0.0), 0.7)
            if canonical_data.get("extracurricular_narratives"):
                section_density["ì°½ì²´"] = max(section_density.get("ì°½ì²´", 0.0), 0.6)
            if canonical_data.get("reading_activities"):
                section_density["?…ì„œ"] = max(section_density.get("?…ì„œ", 0.0), 0.5)
            if canonical_data.get("behavior_opinion"):
                section_density["?‰ë™?¹ì„±"] = max(section_density.get("?‰ë™?¹ì„±", 0.0), 0.5)

        quality_report = analysis_artifact.get("quality_report")
        if isinstance(quality_report, dict):
            missing_sections = quality_report.get("missing_critical_sections")
            if isinstance(missing_sections, list):
                for item in missing_sections:
                    text = _normalize_weak_section_label(str(item))
                    if text:
                        weak_sections.append(text)
            score = quality_report.get("overall_score")
            if isinstance(score, (int, float)) and float(score) < 0.6:
                uncertain_items.append("ê³ ê¸‰ ?Œì´?„ë¼???ˆì§ˆ ?ìˆ˜ê°€ ??•„ ?˜ë™ ê²€? ê? ê¶Œì¥?©ë‹ˆ??")

    contradiction_items: list[dict[str, Any]] = []
    normalized_weak_sections = _dedupe_list([_normalize_weak_section_label(item) for item in weak_sections], limit=20)
    final_weak_sections: list[str] = []
    for section in normalized_weak_sections:
        density = float(section_density.get(section, 0.0))
        if density >= 0.95:
            contradiction_items.append(
                {
                    "section": section,
                    "density": round(density, 3),
                    "reason": "weak_or_missing_conflicts_with_density",
                }
            )
            continue
        final_weak_sections.append(section)
    if contradiction_items:
        uncertain_items.append("?¹ì…˜ ë°€?„ì? ?„ë½ ?íƒœ ê°?ëª¨ìˆœ??ê°ì????ë™ ì¡°ì •?ˆìŠµ?ˆë‹¤.")

    contradiction_check_passed = len(contradiction_items) == 0

    return {
        "major_sections": [
            {
                "section": key,
                "density": value,
                "confidence": "high" if value >= 0.6 else "medium" if value >= 0.3 else "low",
            }
            for key, value in section_density.items()
        ],
        "section_density": section_density,
        "timeline_signals": timeline_signals,
        "activity_clusters": activity_clusters,
        "subject_major_alignment_signals": alignment_signals,
        "weak_sections": _dedupe_list(final_weak_sections, limit=10),
        "continuity_signals": continuity_signals,
        "process_reflection_signals": process_reflection_signals,
        "uncertain_items": _dedupe_list(uncertain_items, limit=8),
        "coverage_check": {
            "required_sections": list(_REQUIRED_NORMALIZED_SECTIONS),
            "missing_required_sections": section_coverage.get("missing_sections", []) if isinstance(section_coverage, dict) else [],
            "coverage_score": section_coverage.get("coverage_score", 0.0) if isinstance(section_coverage, dict) else 0.0,
            "reanalysis_required": bool(section_coverage.get("reanalysis_required")) if isinstance(section_coverage, dict) else False,
        },
        "contradiction_check": {
            "passed": contradiction_check_passed,
            "items": contradiction_items,
        },
    }


def _legacy_section_density_from_canonical(canonical_schema: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(canonical_schema, dict):
        return {}
    section_classification = canonical_schema.get("section_classification")
    if not isinstance(section_classification, dict):
        return {}

    legacy_map = {
        "subject_special_notes": "?¸íŠ¹",
        "extracurricular": "ì°½ì²´",
        "career_signals": "ì§„ë¡œ",
        "behavior_opinion": "?‰ë™?¹ì„±",
        "grades_subjects": "êµê³¼?™ìŠµë°œë‹¬?í™©",
        "reading_activity": "?…ì„œ",
    }
    density: dict[str, float] = {}
    for canonical_key, legacy_key in legacy_map.items():
        payload = section_classification.get(canonical_key)
        if not isinstance(payload, dict):
            continue
        try:
            score = max(0.0, min(1.0, float(payload.get("density") or 0.0)))
        except (TypeError, ValueError):
            continue
        density[legacy_key] = max(density.get(legacy_key, 0.0), round(score, 3))
    return density


def _extract_canonical_string_values(
    canonical_schema: dict[str, Any] | None,
    field: str,
    key: str,
) -> list[str]:
    if not isinstance(canonical_schema, dict):
        return []
    raw_values = canonical_schema.get(field)
    if not isinstance(raw_values, list):
        return []
    values: list[str] = []
    for item in raw_values:
        if isinstance(item, dict):
            value = str(item.get(key) or "").strip()
            if value:
                values.append(value)
    return values


def _extract_cluster_hints(text: str) -> list[str]:
    cluster_keywords: dict[str, tuple[str, ...]] = {
        "?êµ¬/?¤í—˜": ("?êµ¬", "?¤í—˜", "ê°€??, "ê²€ì¦?),
        "?°ì´??ë¶„ì„": ("?°ì´??, "?µê³„", "ë¶„ì„", "ì§€??),
        "?„ë¡œ?íŠ¸/?œì•ˆ": ("?„ë¡œ?íŠ¸", "?¤ê³„", "?œì•ˆ", "ê¸°íš"),
        "ê³µë™ì²?ë¦¬ë”??: ("?‘ì—…", "ë¦¬ë”", "ë´‰ì‚¬", "ê³µë™ì²?),
    }
    found: list[str] = []
    lowered = text.lower()
    for label, keywords in cluster_keywords.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            found.append(label)
    return _dedupe_list(found, limit=6)


def _extract_alignment_hints(text: str) -> list[str]:
    patterns = (
        "?„ê³µ",
        "ì§„ë¡œ",
        "?™ê³¼",
        "ê´€??ë¶„ì•¼",
        "?¬ë§",
        "?í•©",
        "?°ê³„",
    )
    hints = _extract_keyword_sentences(text, keywords=patterns, limit=6)
    if not hints:
        return ["?„ê³µ ?°ê³„ ë¬¸ì¥ ? í˜¸ê°€ ?œí•œ?ì…?ˆë‹¤. ?µì‹¬ ê³¼ëª©ê³?ëª©í‘œ ?„ê³µ ?°ê²°??ë¬¸ì¥?¼ë¡œ ë³´ê°•?˜ì„¸??"]
    return hints


def _extract_keyword_sentences(text: str, *, keywords: tuple[str, ...], limit: int) -> list[str]:
    if not text:
        return []
    sentences = re.split(r"(?<=[.!???)\s+|\n+", text)
    collected: list[str] = []
    for sentence in sentences:
        normalized = sentence.strip()
        if len(normalized) < 8:
            continue
        lowered = normalized.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            collected.append(normalized[:180])
        if len(collected) >= limit:
            break
    return _dedupe_list(collected, limit=limit)


def _dedupe_list(items: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in items:
        normalized = str(raw or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
        if len(output) >= limit:
            break
    return output


def _normalize_weak_section_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    alias_map = {
        "grades_subjects": "êµê³¼?™ìŠµë°œë‹¬?í™©",
        "subject_special_notes": "?¸íŠ¹",
        "creative_activities": "ì°½ì²´",
        "extracurricular": "ì°½ì²´",
        "volunteer": "ì°½ì²´",
        "career_signals": "ì§„ë¡œ",
        "reading": "?…ì„œ",
        "reading_activity": "?…ì„œ",
        "behavior_general_comments": "?‰ë™?¹ì„±",
        "behavior_opinion": "?‰ë™?¹ì„±",
        "awards": "?˜ìƒê²½ë ¥",
        "attendance": "ì¶œê²°?í™©",
        "student_info": "?¸ì ?¬í•­",
        "grades_and_notes": "êµê³¼?™ìŠµë°œë‹¬?í™©",
    }
    return alias_map.get(text, text)
