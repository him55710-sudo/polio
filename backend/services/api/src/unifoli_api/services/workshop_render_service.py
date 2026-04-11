from __future__ import annotations

import json
from typing import Any, AsyncIterator

from unifoli_api.core.config import get_settings
from unifoli_api.core.llm import get_llm_client, get_llm_temperature

from unifoli_api.services.quality_control import (
    build_quality_control_metadata,
    get_quality_profile,
    resolve_advanced_features,
)
from unifoli_api.services.llm_cache_service import CacheRequest, fetch_cached_response, store_cached_response
from unifoli_api.services.prompt_registry import get_prompt_registry
from unifoli_api.services.rag_service import (
    RAGConfig,
    RAGContext,
    build_rag_context,
    build_rag_injection_prompt,
    extract_query_keywords,
)
from unifoli_api.services.search_provider_service import normalize_grounding_source_type
from unifoli_api.services.safety_guard import SafetyFlag, run_safety_check
from unifoli_api.services.visual_support_service import build_visual_support_plan
from unifoli_domain.enums import QualityLevel

_QUALITY_GUARDRAIL_PROMPTS: dict[str, str] = {
    QualityLevel.LOW.value: "system.guardrails.render-quality-low",
    QualityLevel.MID.value: "system.guardrails.render-quality-mid",
    QualityLevel.HIGH.value: "system.guardrails.render-quality-high",
}



class SSEEvent:
    SESSION_READY = "session.ready"
    CONTEXT_UPDATED = "context.updated"
    SUGGESTIONS_UPDATED = "suggestions.updated"
    DRAFT_DELTA = "draft.delta"
    DRAFT_COMPLETED = "draft.completed"
    RENDER_STARTED = "render.started"
    RENDER_PROGRESS = "render.progress"
    RENDER_COMPLETED = "render.completed"
    ARTIFACT_READY = "artifact.ready"
    SAFETY_CHECKED = "safety.checked"
    ERROR = "error"


def _sse_line(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"




def _supports_live_generation() -> bool:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return True
    api_key = settings.gemini_api_key
    return bool(api_key and api_key != "DUMMY_KEY")


def _current_model_name() -> str:
    from unifoli_api.core.config import get_settings

    settings = get_settings()
    if settings.llm_provider == "ollama":
        return settings.ollama_model
    return "gemini-1.5-pro"


def _clip(text: str, *, length: int = 160) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= length:
        return normalized
    return f"{normalized[:length].rstrip()}..."


def _turn_display_text(turn: Any) -> str:
    if getattr(turn, "action_payload", None) and isinstance(turn.action_payload, dict):
        display_label = turn.action_payload.get("display_label")
        if display_label:
            return str(display_label)
    return _clip(getattr(turn, "query", "") or "", length=140)


def _serialize_turns(turns: list[Any]) -> str:
    if not turns:
        return "(?€??ê¸°ë¡ ?†ìŒ)"
    parts: list[str] = []
    for turn in turns:
        role = {"starter": "? íƒ(?œìž‘)", "follow_up": "? íƒ(?„ì†)", "message": "ì§ì ‘ ?…ë ¥"}.get(
            getattr(turn, "turn_type", ""),
            getattr(turn, "turn_type", "message"),
        )
        parts.append(f"[{role}] ?™ìƒ: {_clip(getattr(turn, 'query', '') or '', length=220)}")
    return "\n".join(parts)


def _serialize_references(references: list[Any]) -> str:
    if not references:
        return "(?€??ì°¸ê³ ?ë£Œ ?†ìŒ)"
    return "\n".join(
        f"- [{normalize_grounding_source_type(getattr(reference, 'source_type', None))}] {_clip(getattr(reference, 'text_content', '') or '', length=260)}"
        for reference in references
    )


def _grounded_points(turns: list[Any], references: list[Any], *, limit: int = 4) -> list[tuple[str, str]]:
    points: list[tuple[str, str]] = []
    seen: set[str] = set()
    for turn in turns:
        text = _turn_display_text(turn)
        key = text.lower()
        if key in seen or not text:
            continue
        seen.add(key)
        points.append((text, f"turn:{getattr(turn, 'id', '')}"))
        if len(points) >= limit:
            return points
    for reference in references:
        text = _clip(getattr(reference, "text_content", "") or "", length=120)
        key = text.lower()
        if key in seen or not text:
            continue
        seen.add(key)
        points.append((text, f"reference:{getattr(reference, 'id', '')}"))
        if len(points) >= limit:
            return points
    return points


def _build_render_prompt(
    *,
    turns_text: str,
    references_text: str,
    target_major: str | None,
    target_university: str | None,
    quality_level: str,
    advanced_mode: bool = False,
    rag_injection: str = "",
) -> str:
    profile = get_quality_profile(quality_level)
    guardrail = _build_quality_guardrail(profile.level)
    base_instruction = _build_render_base_instruction()

    # ?¬í™” ëª¨ë“œ ?•ìž¥ ì¶œë ¥ ?¤íŽ™
    advanced_output_spec = ""
    if advanced_mode:
        advanced_output_spec = """
  "visual_specs": [
    {
      "type": "chart",
      "chart_spec": {
        "title": "ì°¨íŠ¸ ?œëª©",
        "type": "bar ?ëŠ” line",
        "data": [{"name": "??ª©", "value": ?«ìž}]
      }
    }
  ],
  "math_expressions": [
    {
      "label": "?˜ì‹ ?¤ëª…",
      "latex": "LaTeX ?˜ì‹ ë¬¸ìž??,
      "context": "???˜ì‹???¬ìš©?˜ëŠ” ë§¥ë½"
    }
  ],"""

    rag_section = ""
    if rag_injection:
        rag_section = f"\n{rag_injection}\n"

    return f"""
{base_instruction}

[?„ìž¬ ?ˆì§ˆ ?˜ì?]
- ?˜ì?: {profile.label} ({profile.level})
- ?™ìƒ ?í•©??ê¸°ì?: {profile.student_fit}
- ?ˆì „ ?°ì„ ?? {profile.safety_posture}
- ?¤ì œ??ê·œì¹™: {profile.authenticity_policy}
- ?ˆìœ„ ê²½í—˜ ê°€?œë ˆ?? {profile.hallucination_guardrail}
- ?Œë” ê¹Šì´: {profile.render_depth}
- ?œí˜„ ?ì¹™: {profile.expression_policy}
- ì°¸ê³ ?ë£Œ ê°•ë„: {profile.reference_intensity}
- ?¬í™” ëª¨ë“œ: {'?œì„±' if advanced_mode else 'ë¹„í™œ??}

[?™ìƒ ëª©í‘œ]
- ëª©í‘œ ?€?? {target_university or 'ë¯¸ì •'}
- ëª©í‘œ ?„ê³µ: {target_major or 'ë¯¸ì •'}

[?™ìƒ???¤ì œë¡?ë§í•œ ?Œí¬??ë§¥ë½]
{turns_text}

[?€??ì°¸ê³ ?ë£Œ]
{references_text}
{rag_section}
{guardrail}

[ë°˜ë“œ??ì§€??ê·œì¹™]
- ??ë§¥ë½???†ëŠ” ê²½í—˜, ?˜ì¹˜, ?¤í—˜ ê²°ê³¼, ?¸í„°ë·? ?¼ë¬¸ ?½ì? ?¬ì‹¤???ˆë? ?ì„±?˜ì? ë§ˆë¼.
- ê·¼ê±°ê°€ ë¶€ì¡±í•œ ?´ìš©?€ ?„ë£Œ???œë™ì²˜ëŸ¼ ?°ì? ë§ê³  'ì¶”ê? ?•ì¸ ?„ìš”' ?ëŠ” 'ì¶”ê?ë¡??´íŽ´ë³????¼ë¡œ ì²˜ë¦¬?˜ë¼.
- ?™ìƒ???¤ì œë¡???ê²ƒê³¼ ?¸ë? ?ë£Œ ?´ì„???žì? ë§ˆë¼.
- JSON ?¸ì˜ ?ìŠ¤?¸ë? ì¶œë ¥?˜ì? ë§ˆë¼.
{'- ?¬í™” ëª¨ë“œ?ì„œ???°ì´???œê°??chart_spec)?€ ?˜ì‹(math_expressions)??ê°€?¥í•œ ê²½ìš°?ë§Œ ì¶”ê??˜ë¼.' if advanced_mode else ''}
{'- ì°¨íŠ¸/?˜ì‹???„ìš” ?†ìœ¼ë©?ë¹?ë°°ì—´ë¡??ë¼.' if advanced_mode else ''}

[ì¶œë ¥ JSON]
{{
  "report_markdown": "## ?êµ¬ ë³´ê³ ??\n\\n?™ìƒ ?˜ì?ê³??¤ì œ ë§¥ë½??ë§žëŠ” ë³¸ë¬¸",
  "teacher_record_summary_500": "êµì‚¬ê°€ ê¸°ë¡??ë°˜ì˜?????ˆëŠ” 500???´ë‚´ ?”ì•½",
  "student_submission_note": "?™ìƒ ?œì¶œ ???ê? ë©”ëª¨",
  "evidence_map": {{
    "ì£¼ìž¥ 1": {{"ê·¼ê±°": "?Œí¬???€???ëŠ” ì°¸ê³ ?ë£Œ", "ì¶œì²˜": "turn:... ?ëŠ” reference:..."}}
  }},{advanced_output_spec}
}}
""".strip()


def _build_safe_artifact(
    *,
    turns: list[Any],
    references: list[Any],
    target_major: str | None,
    target_university: str | None,
    quality_level: str,
    summary_note: str | None = None,
) -> dict[str, Any]:
    profile = get_quality_profile(quality_level)
    points = _grounded_points(turns, references)
    point_lines = [f"- {text}" for text, _ in points] or ["- ?™ìƒ???Œí¬?µì—???œê³µ??ë§¥ë½????ëª¨ì„ ?„ìš”ê°€ ?ˆìŠµ?ˆë‹¤."]
    reference_lines = [
        f"- {_clip(getattr(reference, 'text_content', '') or '', length=110)}"
        for reference in references[:2]
    ] or ["- ?„ìž¬ ê³ ì •??ì°¸ê³ ?ë£Œê°€ ?†ìŠµ?ˆë‹¤."]
    evidence_map = {
        f"ì£¼ìž¥ {index}": {"ê·¼ê±°": text, "ì¶œì²˜": source}
        for index, (text, source) in enumerate(points, start=1)
    }
    if not evidence_map:
        evidence_map["ì£¼ìž¥ 1"] = {"ê·¼ê±°": "?Œí¬??ë§¥ë½ ì¶”ê? ?„ìš”", "ì¶œì²˜": "turn:none"}

    intro = f"{target_major or '?¬ë§ ?„ê³µ'} ë§¥ë½?ì„œ ?´ë²ˆ ?êµ¬ë¥??•ë¦¬?©ë‹ˆ??"
    verification_line = summary_note or "?¤ì œë¡??•ì¸???´ìš©ë§??¨ê¸°ê³? ?•ì¸?˜ì? ?Šì? ?´ìš©?€ ê³„íš ?ëŠ” ì¶”ê? ?•ì¸ ??ª©?¼ë¡œ ?¡ë‹ˆ??"

    if profile.level == QualityLevel.LOW.value:
        report_markdown = "\n".join(
            [
                "## ?êµ¬ ë³´ê³ ??,
                "",
                "### 1. ?êµ¬ ë°©í–¥",
                intro,
                "",
                "### 2. ?¤ì œë¡??•ì¸??ë§¥ë½",
                *point_lines,
                "",
                "### 3. ?´ë²ˆ ?™ê¸° ?ˆì— ê°€?¥í•œ ?˜í–‰",
                "- êµê³¼ ê°œë…ê³?ì§ì ‘ ?°ê²°?˜ëŠ” ?œë™ë§??¨ê¹?ˆë‹¤.",
                "- ?™ìƒ??ì§ì ‘ ?¤ëª… ê°€?¥í•œ ê³¼ì •ë§?ê¸°ë¡?©ë‹ˆ??",
                "",
                "### 4. ?ê? ë©”ëª¨",
                f"- {verification_line}",
            ]
        )
        teacher_summary = (
            f"{target_major or 'ê´€???„ê³µ'} ê´€???êµ¬ë¥?êµê³¼ ê°œë… ì¤‘ì‹¬?¼ë¡œ ?•ë¦¬?˜ë©°, "
            f"?Œí¬?µì—???•ì¸???œë™ê³??œí˜„ë§??¨ê²¨ ?™ìƒ ?˜ì???ë§žëŠ” ?ˆì „??ê¸°ë¡ ë°©í–¥???¤ê³„?? "
            f"{' '.join(text for text, _ in points[:2]) or '?êµ¬ ë§¥ë½??ì¶”ê? ?•ì¸?˜ëŠ” ?œë„'}ë¥?ë°”íƒ•?¼ë¡œ ê³¼ìž¥ ?†ëŠ” ?¸íŠ¹ ë¬¸ìž¥ êµ¬ì„±??ê°€?¥í•¨."
        )
    elif profile.level == QualityLevel.HIGH.value:
        report_markdown = "\n".join(
            [
                "## ?êµ¬ ë³´ê³ ??,
                "",
                "### 1. ?¤ì œ ë§¥ë½ ê¸°ë°˜ ?¬í™” ì§ˆë¬¸",
                intro,
                "",
                "### 2. ?™ìƒ??ì§ì ‘ ë§í•œ ?µì‹¬ ë§¥ë½",
                *point_lines,
                "",
                "### 3. ì°¸ê³ ?ë£Œ?€ ?°ê²°???´ì„",
                *reference_lines,
                "",
                "### 4. ê³¼ìž¥ ë°©ì? ë©”ëª¨",
                f"- {verification_line}",
                "- ?™ìƒ???¤ì œë¡???ê²ƒê³¼ ?¸ë? ?ë£Œ ?´ì„??ë¶„ë¦¬?´ì„œ ê¸°ë¡?©ë‹ˆ??",
            ]
        )
        teacher_summary = (
            f"{target_major or '?¬ë§ ?„ê³µ'}?€ ?°ê²°?˜ëŠ” ?êµ¬ë¥??¤ì œ ?˜í–‰ ë§¥ë½ê³?ì°¸ê³ ?ë£Œë¡?êµ¬ë¶„???•ë¦¬?˜ë©°, "
            f"?™ìƒ??ì§ì ‘ ???œë™ê³??´ì„??ê²½ê³„ë¥?ëª…í™•???¸ì?. "
            f"{' '.join(text for text, _ in points[:2]) or '?Œí¬??ë§¥ë½'}??ì¤‘ì‹¬?¼ë¡œ ?¬í™”???œí˜„???™ìƒ ?˜ì???ë§žê²Œ ?µì œ??"
        )
    else:
        report_markdown = "\n".join(
            [
                "## ?êµ¬ ë³´ê³ ??,
                "",
                "### 1. ?êµ¬ ì§ˆë¬¸",
                intro,
                "",
                "### 2. ?•ë³´??ê·¼ê±°",
                *point_lines,
                "",
                "### 3. ê°„ë‹¨???´ì„ê³??¤ìŒ ?¨ê³„",
                "- êµê³¼ ?‘ìš© ë²”ìœ„?ì„œ ë¹„êµ?€ ?´ì„???œë„?©ë‹ˆ??",
                "- ê²°ë¡ ?€ ê³¼ìž¥?˜ì? ?Šê³  ê´€ì°?ê°€?¥í•œ ë²”ìœ„?ì„œë§??•ë¦¬?©ë‹ˆ??",
                "",
                "### 4. ?ê? ë©”ëª¨",
                f"- {verification_line}",
            ]
        )
        teacher_summary = (
            f"{target_major or 'ê´€???„ê³µ'} ê´€???êµ¬ë¥?êµê³¼ ?‘ìš© ?˜ì??¼ë¡œ êµ¬ì²´?”í•˜ë©? "
            f"?Œí¬?µì—???•ë³´??ê·¼ê±°ë¥?ë°”íƒ•?¼ë¡œ ê°„ë‹¨???´ì„ê³??¤ìŒ ?¨ê³„ë¥??¤ê³„?? "
            f"{' '.join(text for text, _ in points[:2]) or '?™ìƒ???œì‹œ???êµ¬ ë°©í–¥'}??ì¤‘ì‹¬?¼ë¡œ ?¤ì œ ?˜í–‰ ê°€?¥í•œ ê¸°ë¡ ?ë¦„??ë§Œë“¦."
        )

    note_lines = [
        "- ?¤ì œë¡??˜ì? ?Šì? ?œë™, ?˜ì¹˜, ì¶œì²˜??ë°˜ë“œ???? œ?˜ê±°??'ì¶”ê? ?•ì¸ ?„ìš”'ë¡??˜ì •?˜ì„¸??",
        f"- ?„ìž¬ ?ˆì§ˆ ?˜ì??€ {profile.label}?´ë©°, ì°¸ê³ ?ë£Œ ?¬ìš© ê°•ë„??{profile.reference_intensity}?…ë‹ˆ??",
        f"- ?ˆìœ„ ê²½í—˜ ê°€?œë ˆ?? {profile.hallucination_guardrail}",
        "- êµì‚¬ê°€ ?½ì—ˆ?????™ìƒ??ì§ì ‘ ???œë™?¼ë¡œ ë³´ì´?”ì? ìµœì¢… ?•ì¸?˜ì„¸??",
    ]
    if target_university:
        note_lines.append(f"- ëª©í‘œ ?€??{target_university}) ë§žì¶¤ ?œí˜„ë³´ë‹¤ ?¤ì œ ?˜í–‰ ?¬ì‹¤???°ì„ ?˜ì„¸??")

    return {
        "report_markdown": report_markdown.strip(),
        "teacher_record_summary_500": _clip(teacher_summary, length=500),
        "student_submission_note": "\n".join(note_lines),
        "evidence_map": evidence_map,
        "visual_specs": [],
        "math_expressions": [],
    }


def _serialize_checks(checks: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        key: {
            "key": value.key,
            "label": value.label,
            "score": value.score,
            "status": value.status,
            "detail": value.detail,
            "matched_count": value.matched_count,
            "unsupported_count": value.unsupported_count,
        }
        for key, value in checks.items()
    }


async def _generate_with_llm(
    *,
    prompt: str,
    quality_level: str,
) -> AsyncIterator[str]:
    profile = get_quality_profile(quality_level)
    llm = get_llm_client(profile="render")
    system_instruction = _build_render_system_instruction(quality_level=profile.level)
    async for token in llm.stream_chat(
        prompt=prompt,
        system_instruction=system_instruction,
        temperature=max(profile.temperature, get_llm_temperature(profile="render")),
    ):
        yield token


async def stream_render(
    db: Session,
    session_id: str,
    project_id: str,
    turns: list[Any],
    references: list[Any],
    target_major: str | None,
    target_university: str | None,
    artifact_id: str,
    quality_level: str = QualityLevel.MID.value,
    advanced_mode: bool = False,
    rag_config: RAGConfig | None = None,
) -> AsyncIterator[str]:
    profile = get_quality_profile(quality_level)
    turns_text = _serialize_turns(turns)
    references_text = _serialize_references(references)
    requested_advanced_mode = advanced_mode
    effective_advanced_mode, advanced_reason = resolve_advanced_features(
        requested=requested_advanced_mode,
        quality_level=profile.level,
        reference_count=len(references),
    )

    # ?¬í™” ëª¨ë“œ RAG ì»¨í…?¤íŠ¸ ë¹Œë“œ
    rag_injection = ""
    rag_context: RAGContext | None = None
    if effective_advanced_mode and rag_config and rag_config.enabled:
        keywords = extract_query_keywords(
            target_major=target_major,
            turns=turns,
        )
        rag_context = await build_rag_context(
            db,
            project_id=project_id,
            query_keywords=keywords,
            pinned_references=references,
            config=rag_config,
        )
        rag_injection = build_rag_injection_prompt(rag_context)

    prompt = _build_render_prompt(
        turns_text=turns_text,
        references_text=references_text,
        target_major=target_major,
        target_university=target_university,
        quality_level=profile.level,
        advanced_mode=effective_advanced_mode,
        rag_injection=rag_injection,
    )
    settings = get_settings()
    cache_request = CacheRequest(
        feature_name="workshop_render.stream_render",
        model_name=_current_model_name(),
        scope_key=f"project:{project_id}",
        config_version=settings.llm_cache_version,
        ttl_seconds=settings.llm_cache_ttl_seconds if settings.llm_cache_enabled else 0,
        bypass=not settings.llm_cache_enabled,
        response_format="text",
        evidence_keys=[
            *(f"turn:{getattr(turn, 'id', '')}" for turn in turns),
            *(f"reference:{getattr(reference, 'id', '')}" for reference in references),
            *((rag_context.evidence_keys if rag_context else [])),
        ],
        payload={
            "prompt": prompt,
            "quality_level": profile.level,
            "advanced_mode_requested": requested_advanced_mode,
            "advanced_mode": effective_advanced_mode,
        },
    )

    yield _sse_line(
        SSEEvent.RENDER_STARTED,
        {
            "artifact_id": artifact_id,
            "session_id": session_id,
            "quality_level": profile.level,
            "quality_label": profile.label,
            "advanced_mode_requested": requested_advanced_mode,
            "advanced_mode": effective_advanced_mode,
            "advanced_reason": advanced_reason,
            "rag_enhanced": bool(rag_context and rag_context.is_enhanced),
            "message": f"[{profile.label}]{' ?”¬?¬í™”' if effective_advanced_mode else ''} ?ˆì „ ì¤‘ì‹¬ ?Œë”ë§ì„ ?œìž‘?©ë‹ˆ??",
        },
    )
    yield _sse_line(
        SSEEvent.CONTEXT_UPDATED,
        {
            "turn_count": len(turns),
            "reference_count": len(references),
            "quality_level": profile.level,
            "advanced_mode_requested": requested_advanced_mode,
            "advanced_mode": effective_advanced_mode,
            "rag_papers_count": len(rag_context.papers) if rag_context else 0,
        },
    )

    full_text = ""
    buffer = ""
    used_fallback = not _supports_live_generation()
    cached_text = fetch_cached_response(db, cache_request)
    if cached_text:
        full_text = cached_text
        used_fallback = False

    if not full_text and _supports_live_generation():
        try:
            chunk_count = 0
            async for token in _generate_with_llm(prompt=prompt, quality_level=profile.level):
                full_text += token
                buffer += token
                chunk_count += 1
                if len(buffer) >= 240:
                    yield _sse_line(SSEEvent.DRAFT_DELTA, {"delta": buffer})
                    buffer = ""
                if chunk_count % 24 == 0:
                    yield _sse_line(
                        SSEEvent.RENDER_PROGRESS,
                        {
                            "chars_generated": len(full_text),
                            "message": f"{len(full_text)}???ì„± ì¤‘ìž…?ˆë‹¤.",
                        },
                    )
        except Exception:
            used_fallback = True

    if used_fallback:
        fallback_artifact = _build_safe_artifact(
            turns=turns,
            references=references,
            target_major=target_major,
            target_university=target_university,
            quality_level=profile.level,
        )
        full_text = json.dumps(fallback_artifact, ensure_ascii=False)
        yield _sse_line(
            SSEEvent.RENDER_PROGRESS,
            {
                "chars_generated": len(full_text),
                "message": "?¸ë? ?ì„±ê¸??†ì´ ?ˆì „ ì´ˆì•ˆ??êµ¬ì„±?ˆìŠµ?ˆë‹¤.",
            },
        )

    if full_text:
        store_cached_response(db, cache_request, response_payload=full_text)

    if buffer:
        yield _sse_line(SSEEvent.DRAFT_DELTA, {"delta": buffer})
    elif cached_text:
        for start in range(0, len(full_text), 240):
            yield _sse_line(SSEEvent.DRAFT_DELTA, {"delta": full_text[start : start + 240]})

    yield _sse_line(SSEEvent.DRAFT_COMPLETED, {"total_chars": len(full_text)})

    parsed = _parse_artifact(full_text)
    safety = run_safety_check(
        report_markdown=parsed.get("report_markdown", ""),
        teacher_summary=parsed.get("teacher_record_summary_500", ""),
        requested_level=profile.level,
        turn_count=len(turns),
        reference_count=len(references),
        turns_text=turns_text,
        references_text=references_text,
    )

    repair_applied = False
    repair_strategy: str | None = None
    critical_flags = {
        SafetyFlag.FABRICATION_RISK.value,
        SafetyFlag.FEASIBILITY_RISK.value,
        SafetyFlag.LEVEL_OVERFLOW.value,
    }
    if safety.downgraded or any(flag in critical_flags for flag in safety.flags):
        repair_applied = True
        repair_strategy = "deterministic_safe_rewrite"
        repaired_level = safety.recommended_level
        parsed = _build_safe_artifact(
            turns=turns,
            references=references,
            target_major=target_major,
            target_university=target_university,
            quality_level=repaired_level,
            summary_note=safety.summary,
        )
        safety = run_safety_check(
            report_markdown=parsed.get("report_markdown", ""),
            teacher_summary=parsed.get("teacher_record_summary_500", ""),
            requested_level=repaired_level,
            turn_count=len(turns),
            reference_count=len(references),
            turns_text=turns_text,
            references_text=references_text,
        )

    planned_visual_support = build_visual_support_plan(
        report_markdown=str(parsed.get("report_markdown", "") or ""),
        evidence_map=parsed.get("evidence_map") or {},
        student_submission_note=str(parsed.get("student_submission_note", "") or ""),
        turns=turns,
        references=references,
        advanced_mode=effective_advanced_mode and not repair_applied,
        target_major=target_major,
    )
    parsed["visual_specs"] = planned_visual_support.get("visual_specs", [])
    parsed["math_expressions"] = planned_visual_support.get("math_expressions", [])

    advanced_features_applied = bool(parsed.get("visual_specs") or parsed.get("math_expressions"))
    if requested_advanced_mode and repair_applied:
        advanced_reason = "?ˆì „ ?¬ìž‘??ê³¼ì •?ì„œ ê³ ê¸‰ ?•ìž¥???œê±°?˜ê³  ?™ìƒ ?˜ì? ì¤‘ì‹¬ ê²°ê³¼ë¡??˜ëŒ?¸ìŠµ?ˆë‹¤."
    elif requested_advanced_mode and used_fallback and not advanced_features_applied:
        advanced_reason = "?ˆì „??ê²°ì •???Œë”ë¥??¬ìš©??ê³ ê¸‰ ?•ìž¥???ìš©?˜ì? ?Šì•˜?µë‹ˆ??"
    elif requested_advanced_mode and effective_advanced_mode and not advanced_features_applied:
        advanced_reason = "ê³ ê¸‰ ?•ìž¥???”ì²­?ˆì?ë§??„ìž¬ ë§¥ë½?ì„œ???ìŠ¤??ê¸°ë°˜ ê²°ê³¼ê°€ ???ˆì „??ì°¨íŠ¸/?˜ì‹???ëžµ?ˆìŠµ?ˆë‹¤."

    checks_payload = _serialize_checks(safety.checks)
    yield _sse_line(
        SSEEvent.SAFETY_CHECKED,
        {
            "safety_score": safety.safety_score,
            "flags": safety.flags,
            "recommended_level": safety.recommended_level,
            "downgraded": safety.downgraded,
            "summary": safety.summary,
            "checks": checks_payload,
        },
    )

    quality_control = build_quality_control_metadata(
        requested_level=profile.level,
        applied_level=safety.recommended_level,
        turn_count=len(turns),
        reference_count=len(references),
        safety_score=safety.safety_score,
        downgraded=safety.downgraded,
        summary=safety.summary,
        flags=safety.flags,
        checks=checks_payload,
        repair_applied=repair_applied or used_fallback,
        repair_strategy=repair_strategy or ("direct_safe_render" if used_fallback else None),
        advanced_features_requested=requested_advanced_mode,
        advanced_features_applied=advanced_features_applied,
        advanced_features_reason=advanced_reason,
    )

    artifact_payload = {
        "artifact_id": artifact_id,
        **parsed,
        "safety": {
            "score": safety.safety_score,
            "flags": safety.flags,
            "recommended_level": safety.recommended_level,
            "downgraded": safety.downgraded,
            "summary": safety.summary,
            "quality_level_applied": safety.recommended_level,
            "checks": checks_payload,
        },
        "quality_control": quality_control,
    }

    yield _sse_line(SSEEvent.ARTIFACT_READY, artifact_payload)
    yield _sse_line(
        SSEEvent.RENDER_COMPLETED,
        {
            "artifact_id": artifact_id,
            "status": "completed",
            "quality_level": safety.recommended_level,
            "safety_score": safety.safety_score,
        },
    )


def _parse_artifact(raw: str) -> dict[str, Any]:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = [line for line in cleaned.split("\n") if not line.startswith("```")]
            cleaned = "\n".join(lines).strip()
        parsed = json.loads(cleaned)
        return {
            "report_markdown": parsed.get("report_markdown", ""),
            "teacher_record_summary_500": parsed.get("teacher_record_summary_500", ""),
            "student_submission_note": parsed.get("student_submission_note", ""),
            "evidence_map": parsed.get("evidence_map", {}),
            "visual_specs": parsed.get("visual_specs", []),
            "math_expressions": parsed.get("math_expressions", []),
        }
    except Exception:
        return {
            "report_markdown": raw,
            "teacher_record_summary_500": "",
            "student_submission_note": "",
            "evidence_map": {},
            "visual_specs": [],
            "math_expressions": [],
        }


def _build_render_base_instruction() -> str:
    return get_prompt_registry().compose_prompt("drafting.report-render")


def _build_render_system_instruction(*, quality_level: str) -> str:
    profile = get_quality_profile(quality_level)
    return (
        f"{get_prompt_registry().compose_prompt('drafting.provenance-boundary')}\n\n"
        f"Current quality level: {profile.label} ({profile.level}). "
        "Return only valid JSON that matches the requested artifact contract."
    )


def _build_quality_guardrail(quality_level: str) -> str:
    prompt_name = _QUALITY_GUARDRAIL_PROMPTS.get(
        quality_level,
        _QUALITY_GUARDRAIL_PROMPTS[QualityLevel.MID.value],
    )
    return get_prompt_registry().compose_prompt(prompt_name)
