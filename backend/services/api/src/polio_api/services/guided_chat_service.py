from __future__ import annotations

import json
from typing import Iterable

from sqlalchemy.orm import Session

from polio_api.core.llm import get_llm_client
from polio_api.db.models.user import User
from polio_api.schemas.guided_chat import (
    GuidedChatStartResponse,
    GuidedChatStatePayload,
    OutlineSection,
    PageRangeOption,
    TopicSelectionResponse,
    TopicSuggestion,
    TopicSuggestionResponse,
)
from polio_api.services.guided_chat_context_service import GuidedChatContext, build_guided_chat_context
from polio_api.services.guided_chat_state_service import load_guided_chat_state, save_guided_chat_state
from polio_api.services.prompt_registry import get_prompt_registry

GUIDED_CHAT_GREETING = "안녕하세요. 어떤 주제의 보고서를 써볼까요?"
LIMITED_CONTEXT_NOTE = "현재 확인 가능한 학생 맥락이 충분하지 않아 제한된 근거 기반으로 보수적으로 제안드립니다."


def start_guided_chat(*, db: Session, user: User, project_id: str | None) -> GuidedChatStartResponse:
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    return GuidedChatStartResponse(
        greeting=GUIDED_CHAT_GREETING,
        project_id=context.project_id,
        evidence_gap_note=_evidence_gap_note(context),
    )


async def generate_topic_suggestions(
    *,
    db: Session,
    user: User,
    project_id: str | None,
    subject: str,
) -> TopicSuggestionResponse:
    normalized_subject = _normalize_subject(subject)
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    llm_response = await _try_llm_topic_suggestions(subject=normalized_subject, context=context)

    normalized = _normalize_suggestions(
        suggestions=llm_response.suggestions if llm_response else [],
        subject=normalized_subject,
        context=context,
    )
    response = TopicSuggestionResponse(
        greeting=GUIDED_CHAT_GREETING,
        subject=normalized_subject,
        suggestions=normalized,
        evidence_gap_note=_evidence_gap_note(context) or (llm_response.evidence_gap_note if llm_response else None),
    )

    if context.project_id:
        save_guided_chat_state(
            db,
            context.project_id,
            GuidedChatStatePayload(
                subject=response.subject,
                suggestions=response.suggestions,
                selected_topic_id=None,
                recommended_page_ranges=[],
                recommended_outline=[],
                starter_draft_markdown=None,
            ),
        )

    return response


def select_topic(
    *,
    db: Session,
    user: User,
    project_id: str | None,
    selected_topic_id: str,
    subject: str | None,
    suggestions: list[TopicSuggestion],
) -> TopicSelectionResponse:
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    normalized_subject = _normalize_subject(subject or "탐구")
    current_suggestions = suggestions
    if not current_suggestions and context.project_id:
        saved = load_guided_chat_state(db, context.project_id)
        if saved is not None:
            current_suggestions = saved.suggestions
            if saved.subject:
                normalized_subject = _normalize_subject(saved.subject)

    normalized = _normalize_suggestions(
        suggestions=current_suggestions,
        subject=normalized_subject,
        context=context,
    )
    selected = next((item for item in normalized if item.id == selected_topic_id), normalized[0])
    page_ranges = _build_page_ranges(context=context, selected=selected)
    outline = _build_outline(context=context, selected=selected)
    starter_draft = _build_starter_markdown(
        subject=normalized_subject,
        selected=selected,
        outline=outline,
        context=context,
    )

    guidance_parts = [f"선택하신 주제는 '{selected.title}'입니다."]
    if context.known_target_info.get("target_major"):
        guidance_parts.append(
            f"현재 확인된 목표 학과('{context.known_target_info['target_major']}')와의 연결성을 중심으로 구조를 잡아드렸습니다."
        )
    else:
        guidance_parts.append("목표 대학/학과 정보가 제한적이어서 보수적으로 구조를 제안드렸습니다.")
    if context.evidence_gaps:
        guidance_parts.append("근거가 부족한 항목은 초안에 '추가 확인 필요'로 남겨 안전하게 진행해 주시면 좋겠습니다.")
    guidance_message = " ".join(guidance_parts)

    response = TopicSelectionResponse(
        selected_topic_id=selected.id,
        selected_title=selected.title,
        recommended_page_ranges=page_ranges,
        recommended_outline=outline,
        starter_draft_markdown=starter_draft,
        guidance_message=guidance_message,
    )

    if context.project_id:
        save_guided_chat_state(
            db,
            context.project_id,
            GuidedChatStatePayload(
                subject=normalized_subject,
                suggestions=normalized,
                selected_topic_id=response.selected_topic_id,
                recommended_page_ranges=response.recommended_page_ranges,
                recommended_outline=response.recommended_outline,
                starter_draft_markdown=response.starter_draft_markdown,
            ),
        )
    return response


async def _try_llm_topic_suggestions(*, subject: str, context: GuidedChatContext) -> TopicSuggestionResponse | None:
    llm = get_llm_client()
    prompt = _build_topic_prompt(subject=subject, context=context)
    system_instruction = get_prompt_registry().compose_prompt("chat.guided-report-topic-orchestration")
    try:
        return await llm.generate_json(
            prompt=prompt,
            response_model=TopicSuggestionResponse,
            system_instruction=system_instruction,
            temperature=0.15,
        )
    except Exception:
        return None


def _build_topic_prompt(*, subject: str, context: GuidedChatContext) -> str:
    context_payload = {
        "known_student_profile": context.known_student_profile,
        "known_target_info": context.known_target_info,
        "diagnosis_summary": context.diagnosis_summary,
        "record_flow_summary": context.record_flow_summary,
        "prior_topics": context.prior_topics,
        "prior_draft_signals": context.prior_draft_signals,
        "workshop_history": context.workshop_history,
        "project_discussion_log": context.project_discussion_log,
        "evidence_gaps": context.evidence_gaps,
    }
    return (
        f"[사용자 입력 과목]\n{subject}\n\n"
        "[학생 맥락 JSON]\n"
        f"{json.dumps(context_payload, ensure_ascii=False, indent=2)}\n\n"
        "[요청 사항]\n"
        "- 반드시 TopicSuggestionResponse 스키마로 JSON만 출력해 주십시오.\n"
        "- 제안 주제는 정확히 3개만 제시해 주십시오.\n"
        "- 학생 근거가 부족하면 evidence_gap_note에 분명히 밝혀 주십시오.\n"
        "- 과장된 합격 보장 표현은 금지해 주십시오.\n"
    )


def _normalize_suggestions(
    *,
    suggestions: Iterable[TopicSuggestion],
    subject: str,
    context: GuidedChatContext,
) -> list[TopicSuggestion]:
    normalized: list[TopicSuggestion] = []
    for index, item in enumerate(suggestions):
        normalized.append(
            TopicSuggestion(
                id=item.id or f"topic-{index + 1}",
                title=_clip_line(item.title, f"{subject} 탐구 확장 주제 {index + 1}"),
                why_fit_student=_clip_line(item.why_fit_student, _fallback_fit_message(context, subject)),
                link_to_record_flow=_clip_line(item.link_to_record_flow, _fallback_record_link(context)),
                link_to_target_major_or_university=_normalize_optional_text(
                    item.link_to_target_major_or_university or _fallback_target_link(context)
                ),
                novelty_point=_clip_line(item.novelty_point, _fallback_novelty_message(subject, index + 1)),
                caution_note=_normalize_optional_text(item.caution_note or _fallback_caution(context)),
            )
        )
        if len(normalized) == 3:
            break

    if len(normalized) < 3:
        normalized.extend(_build_fallback_topics(subject=subject, context=context, existing=normalized))
    return normalized[:3]


def _build_fallback_topics(
    *,
    subject: str,
    context: GuidedChatContext,
    existing: list[TopicSuggestion],
) -> list[TopicSuggestion]:
    existing_titles = {item.title for item in existing}
    base_title = subject.strip() or "탐구"
    target_hint = context.known_target_info.get("target_major") or context.known_target_info.get("target_university")
    record_hint = context.record_flow_summary or "현재 학생부 근거가 제한적입니다."
    prior_hint = context.prior_topics[0] if context.prior_topics else None

    candidates = [
        (
            f"{base_title} 개념을 기존 활동에 재연결하는 탐구 보고서",
            "기존 활동을 개념으로 다시 설명해 기록 일관성을 높이는 방향입니다.",
            "이미 확인된 활동 흐름과 연결해 과장 없이 확장할 수 있습니다.",
        ),
        (
            f"{base_title} 관찰 결과 비교를 통한 근거 보강 보고서",
            "관찰·비교 단계를 추가해 근거 밀도를 높이는 보수적 확장입니다.",
            "결론보다 과정 중심으로 작성해 입시 안전성을 높일 수 있습니다.",
        ),
        (
            f"{base_title} 후속 질문 중심의 심화 탐구 설계 보고서",
            "기존 주제의 다음 질문을 좁혀 심화 방향을 명확히 하는 구성입니다.",
            "무리한 신규 활동 가정 없이 다음 단계 계획을 제시할 수 있습니다.",
        ),
    ]

    if prior_hint:
        candidates[0] = (
            f"{prior_hint}의 후속 질문을 {base_title} 관점으로 확장한 보고서",
            "이전에 다뤘던 흐름을 이어가므로 연속성과 설득력이 높습니다.",
            "새로운 주제로 보이되 기존 활동 축을 유지해 안전합니다.",
        )
    if target_hint:
        candidates[2] = (
            f"{target_hint} 연계형 {base_title} 탐구 확장 보고서",
            "목표 방향과 연계해 주제 선택의 맥락을 분명히 할 수 있습니다.",
            "전공 연결성을 보여주되 확인된 사실 범위를 넘지 않도록 설계했습니다.",
        )

    result: list[TopicSuggestion] = []
    next_index = len(existing) + 1
    for title, fit, novelty in candidates:
        if title in existing_titles:
            continue
        result.append(
            TopicSuggestion(
                id=f"topic-{next_index}",
                title=title,
                why_fit_student=fit,
                link_to_record_flow=f"기록 연결 근거: {_clip_line(record_hint, '현재 기록 근거가 제한적입니다.')}",
                link_to_target_major_or_university=_fallback_target_link(context),
                novelty_point=novelty,
                caution_note=_fallback_caution(context),
            )
        )
        next_index += 1
        if len(existing) + len(result) >= 3:
            break
    return result


def _build_page_ranges(*, context: GuidedChatContext, selected: TopicSuggestion) -> list[PageRangeOption]:
    limited = bool(context.evidence_gaps)
    major_connected = bool(context.known_target_info.get("target_major") or context.known_target_info.get("target_university"))
    base_options = [
        PageRangeOption(
            label="압축형",
            min_pages=2,
            max_pages=3,
            why_this_length="핵심 근거만 빠르게 정리하기에 적합합니다.",
        ),
        PageRangeOption(
            label="균형형",
            min_pages=3,
            max_pages=4,
            why_this_length="주제 배경, 근거, 성찰을 균형 있게 담기 좋습니다.",
        ),
        PageRangeOption(
            label="심화형",
            min_pages=4,
            max_pages=5,
            why_this_length="비교나 추가 검토를 포함한 확장 설명에 적합합니다.",
        ),
    ]
    if limited:
        base_options[2] = PageRangeOption(
            label="안전 심화형",
            min_pages=4,
            max_pages=4,
            why_this_length="근거가 제한적이므로 과장 없이 한정된 범위에서만 심화하시길 권장드립니다.",
        )
    if major_connected:
        base_options[1] = PageRangeOption(
            label="전공 연결형",
            min_pages=3,
            max_pages=4,
            why_this_length="목표 전공/대학 연결 문단을 포함하기 좋은 길이입니다.",
        )
    return base_options


def _build_outline(*, context: GuidedChatContext, selected: TopicSuggestion) -> list[OutlineSection]:
    outline = [
        OutlineSection(title="1. 주제와 문제의식", purpose="선택한 주제의 필요성과 현재 질문을 간결히 제시합니다."),
        OutlineSection(title="2. 확인된 활동/자료 근거", purpose="학생부·진단·기존 활동 중 확인된 사실만 정리합니다."),
        OutlineSection(title="3. 분석 및 해석", purpose="근거에서 도출되는 해석을 과장 없이 연결합니다."),
        OutlineSection(title="4. 한계와 다음 단계", purpose="근거 부족 지점을 명시하고 실현 가능한 다음 행동을 제안합니다."),
    ]
    if context.known_target_info.get("target_major") or context.known_target_info.get("target_university"):
        outline.insert(
            3,
            OutlineSection(
                title="4. 목표 방향과의 연결",
                purpose="목표 대학/학과와의 연결을 사실 기반으로 짧게 설명합니다.",
            ),
        )
    return outline


def _build_starter_markdown(
    *,
    subject: str,
    selected: TopicSuggestion,
    outline: list[OutlineSection],
    context: GuidedChatContext,
) -> str:
    major = context.known_target_info.get("target_major")
    university = context.known_target_info.get("target_university")
    target_line = " / ".join([value for value in [university, major] if value]) or "미설정"
    limited_note = _evidence_gap_note(context)

    lines = [
        f"# {selected.title}",
        "",
        f"- 과목: {subject}",
        f"- 목표 방향: {target_line}",
        f"- 주제 선정 이유: {selected.why_fit_student}",
        "",
        "## 작성 전 확인",
        f"- 기록 연결: {selected.link_to_record_flow}",
    ]
    if selected.link_to_target_major_or_university:
        lines.append(f"- 목표 연결: {selected.link_to_target_major_or_university}")
    lines.append(f"- 새로움 포인트: {selected.novelty_point}")
    if selected.caution_note:
        lines.append(f"- 주의 사항: {selected.caution_note}")
    if limited_note:
        lines.append(f"- 제한 맥락 안내: {limited_note}")
    lines.append("")
    lines.append("## 초안 구조")
    for section in outline:
        lines.append(f"### {section.title}")
        lines.append(section.purpose)
        lines.append("")
    lines.append("## 메모")
    lines.append("- 확인되지 않은 활동은 쓰지 않습니다.")
    lines.append("- 근거가 부족한 부분은 '추가 확인 필요'로 표시합니다.")
    return "\n".join(lines).strip()


def _normalize_subject(subject: str) -> str:
    clean = " ".join(subject.strip().split())
    return clean or "탐구"


def _fallback_fit_message(context: GuidedChatContext, subject: str) -> str:
    if context.record_flow_summary:
        return f"기존 기록 흐름을 바탕으로 {subject} 주제를 안전하게 확장할 수 있습니다."
    return f"현재 확보된 맥락 범위 안에서 {subject} 주제를 보수적으로 구성하기에 적합합니다."


def _fallback_record_link(context: GuidedChatContext) -> str:
    if context.record_flow_summary:
        return f"확인된 기록 요약: {_clip_line(context.record_flow_summary, '기록 요약이 존재합니다.')}"
    return "학생부 근거가 제한적이어서 사실 확인 가능한 범위만 사용하도록 안내드립니다."


def _fallback_target_link(context: GuidedChatContext) -> str | None:
    major = context.known_target_info.get("target_major")
    university = context.known_target_info.get("target_university")
    if major and university:
        return f"{university} {major} 방향과 연결 가능한 주제로 설계했습니다."
    if major:
        return f"{major} 목표와의 연결 가능성을 중심으로 제안했습니다."
    if university:
        return f"{university} 지원 방향을 고려해 무리 없는 범위에서 제안했습니다."
    return None


def _fallback_novelty_message(subject: str, index: int) -> str:
    if index == 1:
        return f"{subject} 주제에서 기존 활동의 개념 설명 비중을 높여 차별화합니다."
    if index == 2:
        return f"{subject} 주제에서 비교·검토 단계를 명시해 근거 밀도를 높입니다."
    return f"{subject} 주제에서 다음 탐구 질문을 명확히 정의해 연속성을 강화합니다."


def _fallback_caution(context: GuidedChatContext) -> str | None:
    if context.evidence_gaps:
        return "확인되지 않은 활동·수상·결과를 추가하지 않고, 근거 부족 항목은 명시해 주십시오."
    return None


def _evidence_gap_note(context: GuidedChatContext) -> str | None:
    if not context.evidence_gaps:
        return None
    top_gaps = " ".join(context.evidence_gaps[:2])
    return f"{LIMITED_CONTEXT_NOTE} {top_gaps}"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _clip_line(value: str | None, fallback: str, limit: int = 220) -> str:
    normalized = _normalize_optional_text(value) or fallback
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."
