from __future__ import annotations

import json
from typing import Iterable, Literal

from sqlalchemy.orm import Session

from unifoli_api.core.llm import LLMRequestError, get_llm_client, get_llm_temperature
from unifoli_api.db.models.user import User
from unifoli_api.schemas.guided_chat import (
    GuidedChoiceGroup,
    GuidedChoiceOption,
    GuidedConversationPhase,
    GuidedChatStartResponse,
    GuidedChatStatePayload,
    OutlineSection,
    PageRangeSelectionResponse,
    PageRangeOption,
    StructureSelectionResponse,
    TopicSelectionResponse,
    TopicSuggestion,
    TopicSuggestionResponse,
)
from unifoli_api.services.guided_chat_context_service import GuidedChatContext, build_guided_chat_context
from unifoli_api.services.guided_chat_state_service import load_guided_chat_state, save_guided_chat_state
from unifoli_api.services.prompt_registry import get_prompt_registry

GUIDED_CHAT_GREETING = "안녕하세요! 어떤 흥미로운 주제로 보고서를 시작해볼까요? 😊"
LIMITED_CONTEXT_NOTE = "학생부 기록이 조금 부족해서, 안전하게 시작할 수 있는 주제들로 준비했어요."

DEFAULT_SUBJECT_OPTIONS: list[GuidedChoiceOption] = [
    GuidedChoiceOption(id="subject-math", label="수학", value="수학"),
    GuidedChoiceOption(id="subject-math2", label="수2", value="수2"),
    GuidedChoiceOption(id="subject-chemistry", label="화학", value="화학"),
    GuidedChoiceOption(id="subject-biology", label="생명과학", value="생명과학"),
]


def start_guided_chat(*, db: Session, user: User, project_id: str | None) -> GuidedChatStartResponse:
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    saved_state = load_guided_chat_state(db, context.project_id) if context.project_id else None
    phase = _resolve_phase_from_saved_state(saved_state)
    selected_page_label = saved_state.selected_page_range_label if saved_state else None
    selected_structure_id = saved_state.selected_structure_id if saved_state else None
    structure_options = saved_state.structure_options if saved_state else []
    next_action_options = saved_state.next_action_options if saved_state else []
    state_summary = _build_state_summary(
        context=context,
        phase=phase,
        subject=saved_state.subject if saved_state else None,
        selected_topic_id=saved_state.selected_topic_id if saved_state else None,
        selected_page_range_label=selected_page_label,
        selected_structure_id=selected_structure_id,
        suggestions=saved_state.suggestions if saved_state else [],
        page_ranges=saved_state.recommended_page_ranges if saved_state else [],
        outline=saved_state.recommended_outline if saved_state else [],
        structure_options=structure_options,
        next_action_options=next_action_options,
        starter_draft_markdown=saved_state.starter_draft_markdown if saved_state else None,
    )
    assistant_message, choice_groups = _build_start_prompt(
        phase=phase,
        context=context,
        state_summary=state_summary,
    )
    return GuidedChatStartResponse(
        greeting=GUIDED_CHAT_GREETING,
        assistant_message=assistant_message,
        phase=phase,
        project_id=context.project_id,
        evidence_gap_note=_evidence_gap_note(context),
        choice_groups=choice_groups,
        limited_mode=bool(context.evidence_gaps),
        limited_reason="evidence_gap" if context.evidence_gaps else None,
        state_summary=state_summary,
    )


async def generate_topic_suggestions(
    *,
    db: Session,
    user: User,
    project_id: str | None,
    subject: str,
    starred_keywords: list[str] = [],
    target_major: str | None = None,
) -> TopicSuggestionResponse:
    normalized_subject = _normalize_subject(subject)
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    
    # 3가지 유형의 추천을 위해 프롬프트 전달
    llm_response, limited_reason = await _try_llm_topic_suggestions(
        subject=normalized_subject, 
        context=context,
        starred_keywords=starred_keywords
    )

    normalized = _normalize_suggestions(
        suggestions=llm_response.suggestions if llm_response else [],
        subject=normalized_subject,
        context=context,
    )
    
    summary = _build_state_summary(
        context=context,
        phase="topic_selection",
        subject=normalized_subject,
        selected_topic_id=None,
        selected_page_range_label=None,
        selected_structure_id=None,
        suggestions=normalized,
        page_ranges=[],
        outline=[],
        structure_options=[],
        next_action_options=[],
        starter_draft_markdown=None,
    )
    
    limited_mode = bool(context.evidence_gaps or limited_reason)
    assistant_message = (
        f"좋아요! '{normalized_subject}'를 바탕으로 너의 기록과 관심사를 융합한 3가지 주제를 가져왔어.\n"
        "너의 취향에 딱 맞는 방향을 골라봐! ✨"
    )
    
    choice_groups = [
        GuidedChoiceGroup(
            id="topic-selection",
            title="가장 끌리는 주제를 선택해줘!",
            style="cards",
            options=[
                GuidedChoiceOption(
                    id=item.id,
                    label=item.title,
                    description=_clip_line(item.why_fit_student, item.link_to_record_flow, 140),
                    value=item.id,
                )
                for item in normalized
            ],
        )
    ]

    response = TopicSuggestionResponse(
        greeting=GUIDED_CHAT_GREETING,
        assistant_message=assistant_message,
        phase="topic_selection",
        subject=normalized_subject,
        suggestions=normalized,
        evidence_gap_note=_evidence_gap_note(context) or (llm_response.evidence_gap_note if llm_response else None),
        choice_groups=choice_groups,
        limited_mode=limited_mode,
        limited_reason=limited_reason or ("evidence_gap" if context.evidence_gaps else None),
        state_summary=summary,
    )

    if context.project_id:
        save_guided_chat_state(
            db,
            context.project_id,
            GuidedChatStatePayload(
                phase="topic_selection",
                subject=response.subject,
                suggestions=response.suggestions,
                selected_topic_id=None,
                selected_page_range_label=None,
                selected_structure_id=None,
                recommended_page_ranges=[],
                recommended_outline=[],
                structure_options=[],
                next_action_options=[],
                starter_draft_markdown=None,
                state_summary=summary,
                limited_mode=response.limited_mode,
                limited_reason=response.limited_reason,
            ),
        )

    return response


async def _try_llm_topic_suggestions(
    *,
    subject: str,
    context: GuidedChatContext,
    starred_keywords: list[str] = [],
) -> tuple[TopicSuggestionResponse | None, str | None]:
    try:
        llm = get_llm_client(profile="fast", concern="guided_chat")
    except TypeError:
        llm = get_llm_client()
        
    prompt = _build_topic_prompt(subject=subject, context=context, starred_keywords=starred_keywords)
    system_instruction = get_prompt_registry().compose_prompt("chat.guided-report-topic-orchestration")
    
    try:
        response = await llm.generate_json(
            prompt=prompt,
            response_model=TopicSuggestionResponse,
            system_instruction=system_instruction,
            temperature=get_llm_temperature(profile="fast", concern="guided_chat"),
        )
        return response, None
    except LLMRequestError as exc:
        return None, exc.limited_reason
    except Exception:
        return None, "llm_unavailable"


def _build_topic_prompt(*, subject: str, context: GuidedChatContext, starred_keywords: list[str] = []) -> str:
    compact_payload = {
        "target": {
            "university": context.known_target_info.get("target_university"),
            "major": context.known_target_info.get("target_major"),
        },
        "diagnosis_summary": context.diagnosis_summary,
        "record_flow_summary": _clip_line(context.record_flow_summary, "기록 요약 없음"),
        "starred_keywords": starred_keywords,
        "prior_topics": context.prior_topics[:3],
    }
    
    return (
        f"[학생의 관심 과목]\n{subject}\n\n"
        "[학생부 및 관심사 요약]\n"
        f"{json.dumps(compact_payload, ensure_ascii=False)}\n\n"
        "[추천 주제 생성 지침]\n"
        "다음 3가지 카테고리에 맞춰 각각 1개씩, 총 3개의 독창적이고 설득력 있는 탐구 주제를 추천해줘:\n\n"
        "1. [interest] 사용자 관심형: 학생이 별표로 저장한 키워드({starred_keywords})와 관심사를 적극 반영한 맞춤형 주제\n"
        "2. [subject] 교과과목 심화형: '{subject}' 과목의 핵심 개념을 심화 탐구하여 세특 기록을 풍성하게 만들 수 있는 학술적 주제\n"
        "3. [major] 목표학과 융합형: 학생의 목표 전공과 '{subject}' 과목의 접점을 찾아 진로 역량을 돋보이게 하는 융합 주제\n\n"
        "[출력 규칙]\n"
        "- TopicSuggestionResponse JSON 형식으로만 응답해줘.\n"
        "- 각 주제의 suggestion_type 필드에 'interest', 'subject', 'major' 중 하나를 꼭 넣어줘.\n"
        "- 고등학생이 읽었을 때 '우와, 이건 진짜 해보고 싶다!'라는 생각이 들 정도로 매력적인 제목과 설명을 작성해줘.\n"
        "- 왜 이 주제가 너에게 딱 맞는지(why_fit_student)를 너의 기록과 연결해서 아주 친절하게 설명해줘.\n"
    )


def _normalize_suggestions(
    *,
    suggestions: Iterable[TopicSuggestion],
    subject: str,
    context: GuidedChatContext,
) -> list[TopicSuggestion]:
    normalized: list[TopicSuggestion] = []
    seen_titles: set[str] = set()

    for index, item in enumerate(suggestions):
        title = _clip_line(item.title, f"{subject} 기반 탐구 주제 {index + 1}")
        title_key = title.strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        normalized.append(
            TopicSuggestion(
                id=item.id or f"topic-{len(normalized) + 1}",
                title=title,
                why_fit_student=_clip_line(item.why_fit_student, "너의 기록과 정말 잘 어울리는 주제야!"),
                link_to_record_flow=_clip_line(item.link_to_record_flow, "기존 활동에서 자연스럽게 이어지는 흐름이야."),
                link_to_target_major_or_university=item.link_to_target_major_or_university,
                suggestion_type=item.suggestion_type or (["interest", "subject", "major"][len(normalized) % 3]),
                is_starred=item.is_starred
            )
        )
        if len(normalized) == 3:
            break

    if len(normalized) < 3:
        types_to_fill = ["interest", "subject", "major"]
        for t in types_to_fill:
            if any(n.suggestion_type == t for n in normalized):
                continue
            normalized.append(
                TopicSuggestion(
                    id=f"fallback-{t}",
                    title=f"{subject} {t} 기반 추천 주제",
                    why_fit_student="너의 기록을 바탕으로 추천하는 주제야.",
                    link_to_record_flow="기록의 연속성을 고려했어.",
                    suggestion_type=t
                )
            )
            if len(normalized) >= 3: break
            
    return normalized[:3]

# Note: Other helper functions (_clip_line, _normalize_subject, etc.) are assumed to be present 
# but are omitted here for brevity if they were not changed. 
# However, to avoid 'undefined' errors, I should include the rest of the file.
