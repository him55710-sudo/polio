from __future__ import annotations

import json
from typing import Iterable

from sqlalchemy.orm import Session

from unifoli_api.core.llm import LLMRequestError, get_llm_client, get_llm_temperature
from unifoli_api.db.models.user import User
from unifoli_api.schemas.guided_chat import (
    GuidedChatStartResponse,
    GuidedChatStatePayload,
    OutlineSection,
    PageRangeOption,
    TopicSelectionResponse,
    TopicSuggestion,
    TopicSuggestionResponse,
)
from unifoli_api.services.guided_chat_context_service import GuidedChatContext, build_guided_chat_context
from unifoli_api.services.guided_chat_state_service import load_guided_chat_state, save_guided_chat_state
from unifoli_api.services.prompt_registry import get_prompt_registry

GUIDED_CHAT_GREETING = "?덈뀞?섏꽭?? ?대뼡 二쇱젣??蹂닿퀬?쒕? ?⑤낵源뚯슂?"
LIMITED_CONTEXT_NOTE = "?꾩옱 ?뺤씤 媛?ν븳 ?숈깮 留λ씫???쒗븳?섏뼱 蹂댁닔?곸쑝濡??쒖븞?쒕┰?덈떎."


def start_guided_chat(*, db: Session, user: User, project_id: str | None) -> GuidedChatStartResponse:
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    saved_state = load_guided_chat_state(db, context.project_id) if context.project_id else None
    state_summary = _build_state_summary(
        context=context,
        subject=saved_state.subject if saved_state else None,
        selected_topic_id=saved_state.selected_topic_id if saved_state else None,
        suggestions=saved_state.suggestions if saved_state else [],
        outline=saved_state.recommended_outline if saved_state else [],
        starter_draft_markdown=saved_state.starter_draft_markdown if saved_state else None,
    )
    return GuidedChatStartResponse(
        greeting=GUIDED_CHAT_GREETING,
        project_id=context.project_id,
        evidence_gap_note=_evidence_gap_note(context),
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
) -> TopicSuggestionResponse:
    normalized_subject = _normalize_subject(subject)
    context = build_guided_chat_context(db=db, user=user, project_id=project_id)
    llm_response, limited_reason = await _try_llm_topic_suggestions(subject=normalized_subject, context=context)

    normalized = _normalize_suggestions(
        suggestions=llm_response.suggestions if llm_response else [],
        subject=normalized_subject,
        context=context,
    )
    summary = _build_state_summary(
        context=context,
        subject=normalized_subject,
        selected_topic_id=None,
        suggestions=normalized,
        outline=[],
        starter_draft_markdown=None,
    )
    limited_mode = bool(context.evidence_gaps or limited_reason)

    response = TopicSuggestionResponse(
        greeting=GUIDED_CHAT_GREETING,
        subject=normalized_subject,
        suggestions=normalized,
        evidence_gap_note=_evidence_gap_note(context) or (llm_response.evidence_gap_note if llm_response else None),
        limited_mode=limited_mode,
        limited_reason=limited_reason or ("evidence_gap" if context.evidence_gaps else None),
        state_summary=summary,
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
                state_summary=summary,
                limited_mode=response.limited_mode,
                limited_reason=response.limited_reason,
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
    normalized_subject = _normalize_subject(subject or "?먭뎄")
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

    page_ranges = _build_page_ranges(context=context)
    outline = _build_outline(context=context, selected=selected)
    starter_draft = _build_starter_markdown(
        subject=normalized_subject,
        selected=selected,
        outline=outline,
        context=context,
    )

    guidance_parts = [f"?좏깮 二쇱젣??'{selected.title}' ?낅땲??"]
    if context.known_target_info.get("target_major"):
        guidance_parts.append(
            f"紐⑺몴 ?꾧났 '{context.known_target_info['target_major']}'怨??곌껐?섎뒗 ?먮쫫??以묒떖?쇰줈 援ъ“?뷀뻽?듬땲??"
        )
    if context.evidence_gaps:
        guidance_parts.append("洹쇨굅媛 遺議깊븳 吏?먯? '異붽? ?뺤씤 ?꾩슂'濡??쒓린???덉쟾?섍쾶 ?뺤옣?섏꽭??")
    guidance_message = " ".join(guidance_parts)

    summary = _build_state_summary(
        context=context,
        subject=normalized_subject,
        selected_topic_id=selected.id,
        suggestions=normalized,
        outline=outline,
        starter_draft_markdown=starter_draft,
    )

    response = TopicSelectionResponse(
        selected_topic_id=selected.id,
        selected_title=selected.title,
        recommended_page_ranges=page_ranges,
        recommended_outline=outline,
        starter_draft_markdown=starter_draft,
        guidance_message=guidance_message,
        limited_mode=bool(context.evidence_gaps),
        limited_reason="evidence_gap" if context.evidence_gaps else None,
        state_summary=summary,
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
) -> tuple[TopicSuggestionResponse | None, str | None]:
    try:
        llm = get_llm_client(profile="fast")
    except TypeError:
        # Backward compatibility for tests monkeypatching get_llm_client() without kwargs.
        llm = get_llm_client()  # type: ignore[call-arg]
    prompt = _build_topic_prompt(subject=subject, context=context)
    system_instruction = get_prompt_registry().compose_prompt("chat.guided-report-topic-orchestration")
    try:
        response = await llm.generate_json(
            prompt=prompt,
            response_model=TopicSuggestionResponse,
            system_instruction=system_instruction,
            temperature=get_llm_temperature(profile="fast"),
        )
        return response, None
    except LLMRequestError as exc:
        return None, exc.limited_reason
    except Exception:
        return None, "llm_unavailable"


def _build_topic_prompt(*, subject: str, context: GuidedChatContext) -> str:
    compact_payload = {
        "target": {
            "university": context.known_target_info.get("target_university"),
            "major": context.known_target_info.get("target_major"),
        },
        "diagnosis_summary": context.diagnosis_summary,
        "record_flow_summary": _clip_line(context.record_flow_summary, "湲곕줉 ?붿빟 ?놁쓬"),
        "prior_topics": context.prior_topics[:3],
        "evidence_gaps": context.evidence_gaps[:5],
        "history": context.workshop_history[-4:],
        "discussion": context.project_discussion_log[-3:],
    }
    return (
        f"[?낅젰 怨쇰ぉ/二쇱젣]\n{subject}\n\n"
        "[?뺤텞 而⑦뀓?ㅽ듃 JSON]\n"
        f"{json.dumps(compact_payload, ensure_ascii=False)}\n\n"
        "[?붿껌]\n"
        "- TopicSuggestionResponse JSON留?異쒕젰?섏꽭??\n"
        "- ?뺥솗??3媛쒖쓽 ?쒕줈 ?ㅻⅨ 二쇱젣瑜??쒖떆?섏꽭??\n"
        "- ?숈깮 湲곕줉 洹쇨굅媛 ?쏀븯硫?蹂댁닔?곸쑝濡??쒖븞?섍퀬 evidence_gap_note瑜??묒꽦?섏꽭??\n"
        "- 怨쇱옣/?⑷꺽蹂댁옣 ?쒗쁽??湲덉??섏꽭??\n"
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
        title = _clip_line(item.title, f"{subject} 湲곕컲 ?먭뎄 二쇱젣 {index + 1}")
        title_key = title.strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        normalized.append(
            TopicSuggestion(
                id=item.id or f"topic-{len(normalized) + 1}",
                title=title,
                why_fit_student=_clip_line(item.why_fit_student, _fallback_fit_message(context, subject)),
                link_to_record_flow=_clip_line(item.link_to_record_flow, _fallback_record_link(context)),
                link_to_target_major_or_university=_normalize_optional_text(
                    item.link_to_target_major_or_university or _fallback_target_link(context)
                ),
                novelty_point=_clip_line(item.novelty_point, _fallback_novelty_message(subject, len(normalized) + 1)),
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
    base_title = subject.strip() or "?먭뎄"
    target_hint = context.known_target_info.get("target_major") or context.known_target_info.get("target_university")
    record_hint = context.record_flow_summary or "?꾩옱 ?숈깮遺 洹쇨굅媛 ?쒗븳?곸엯?덈떎."

    candidates = [
        (
            f"{base_title} 媛쒕뀗??湲곗〈 ?쒕룞 留λ씫怨??곌껐?섎뒗 ?먭뎄 蹂닿퀬??,
            "湲곗〈 ?쒕룞 留λ씫???ㅼ떆 ?ㅻ챸??湲곕줉 ?곗냽?깆쓣 ?믪씠??諛⑺뼢?낅땲??",
            "異붽? ?ъ떎 媛???놁씠 ?뺤씤???쒕룞 以묒떖?쇰줈 ?뺤옣?⑸땲??",
        ),
        (
            f"{base_title} 愿李?寃곌낵 鍮꾧탳瑜??듯븳 洹쇨굅 蹂닿컯 蹂닿퀬??,
            "鍮꾧탳/寃???④퀎瑜??ｌ뼱 洹쇨굅 諛?꾨? ?믪씠??蹂댁닔??援ъ“?낅땲??",
            "寃곕줎蹂대떎 怨쇱젙 以묒떖?쇰줈 援ъ꽦??怨쇱옣 ?꾪뿕????땅?덈떎.",
        ),
        (
            f"{base_title} ?꾩냽 吏덈Ц 以묒떖???ы솕 ?먭뎄 怨꾪쉷 蹂닿퀬??,
            "吏湲??뺤젙 媛?ν븳 ?댁슜怨?異붽? 寃利앹씠 ?꾩슂???댁슜??遺꾨━?⑸땲??",
            "?ㅽ뻾 媛?ν븳 ?ㅼ쓬 吏덈Ц??紐낆떆???ㅼ젣 ?묒꽦?쇰줈 ?댁뼱吏묐땲??",
        ),
    ]

    if target_hint:
        candidates[2] = (
            f"{target_hint} ?곌퀎??{base_title} ?먭뎄 蹂닿퀬??,
            "紐⑺몴 吏꾨줈? ?곌껐?섎뒗 ?먭뎄 紐⑹쟻??紐낆떆?섎릺 怨쇱옣 ?놁씠 ?묒꽦?⑸땲??",
            "吏꾨줈 ?곌껐?깆쓣 蹂댁뿬二쇰릺 ?뺤씤???ъ떎 踰붿쐞瑜??섏? ?딆뒿?덈떎.",
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
                link_to_record_flow=f"湲곕줉 ?곌껐 洹쇨굅: {_clip_line(record_hint, '?꾩옱 湲곕줉 洹쇨굅媛 ?쒗븳?곸엯?덈떎.')}",
                link_to_target_major_or_university=_fallback_target_link(context),
                novelty_point=novelty,
                caution_note=_fallback_caution(context),
            )
        )
        next_index += 1
        if len(existing) + len(result) >= 3:
            break
    return result


def _build_page_ranges(*, context: GuidedChatContext) -> list[PageRangeOption]:
    limited = bool(context.evidence_gaps)
    return [
        PageRangeOption(
            label="?듭떖??,
            min_pages=3,
            max_pages=4,
            why_this_length="?듭떖 洹쇨굅? 吏덈Ц??鍮좊Ⅴ寃??뺣━?????곹빀?⑸땲??",
        ),
        PageRangeOption(
            label="?쒖???,
            min_pages=4,
            max_pages=5,
            why_this_length="諛곌꼍-洹쇨굅-?댁꽍-?꾩냽怨꾪쉷??洹좏삎 ?덇쾶 ?닿린 醫뗭뒿?덈떎.",
        ),
        PageRangeOption(
            label="?ы솕?? if not limited else "?덉쟾 ?ы솕??,
            min_pages=5 if not limited else 4,
            max_pages=6 if not limited else 5,
            why_this_length=(
                "鍮꾧탳/寃利??④퀎瑜??ы븿???ы솕 ?쒖닠???곹빀?⑸땲??"
                if not limited
                else "洹쇨굅 遺議?援ш컙??紐낆떆?곸쑝濡?遺꾨━???덉쟾?섍쾶 ?ы솕?⑸땲??"
            ),
        ),
    ]


def _build_outline(*, context: GuidedChatContext, selected: TopicSuggestion) -> list[OutlineSection]:
    outline = [
        OutlineSection(title="1. 二쇱젣 ?좎젙 諛곌꼍", purpose="????二쇱젣媛 ?꾩옱 ?숈깮 留λ씫???곹빀?쒖? ?ㅻ챸?⑸땲??"),
        OutlineSection(title="2. 以묒떖 吏덈Ц怨??먭뎄 紐⑹쟻", purpose="??臾몄옣 以묒떖 吏덈Ц???쒖떆?섍퀬 蹂닿퀬??紐⑺몴瑜?紐낇솗???⑸땲??"),
        OutlineSection(title="3. ?뺤씤 媛?ν븳 洹쇨굅", purpose="?숈깮遺/臾몄꽌?먯꽌 ?뺤씤 媛?ν븳 ?ъ떎留??뺣━?⑸땲??"),
        OutlineSection(title="4. 遺꾩꽍怨??댁꽍", purpose="洹쇨굅 湲곕컲 ?댁꽍怨?二쇱옣 寃쎄퀎瑜?援щ텇???묒꽦?⑸땲??"),
        OutlineSection(title="5. 異붽? 寃利?怨꾪쉷", purpose="異붽? ?뺤씤???꾩슂????ぉ怨?蹂닿컯 怨꾪쉷???곸뒿?덈떎."),
    ]
    if context.known_target_info.get("target_major") or context.known_target_info.get("target_university"):
        outline.insert(
            4,
            OutlineSection(title="4-2. 吏꾨줈/?꾧났 ?곌껐", purpose="紐⑺몴 諛⑺뼢怨??곌껐?섎뒗 ?숈뒿 ?섎룄瑜??ъ떎 湲곕컲?쇰줈 ?쒖떆?⑸땲??"),
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
    target_line = " / ".join([value for value in [university, major] if value]) or "誘몄꽕??
    limited_note = _evidence_gap_note(context)

    safe_claims: list[str] = []
    if context.record_flow_summary:
        safe_claims.append(_clip_line(context.record_flow_summary, "湲곕줉 ?붿빟 湲곕컲 洹쇨굅"))
    if selected.link_to_record_flow:
        safe_claims.append(_clip_line(selected.link_to_record_flow, "湲곕줉 ?곌껐 洹쇨굅"))

    unresolved = context.evidence_gaps[:4] or ["異붽? ?뺤씤 ?꾩슂"]

    lines = [
        f"# {selected.title}",
        "",
        f"- 怨쇰ぉ: {subject}",
        f"- 蹂닿퀬??紐⑺몴: {target_line} 諛⑺뼢怨??곌껐?섎뒗 ?먭뎄 ??웾??洹쇨굅 湲곕컲?쇰줈 ?뺣━",
        f"- 以묒떖 吏덈Ц(1臾몄옣): {selected.novelty_point}",
        "",
        "## ????二쇱젣媛 ?숈깮?먭쾶 留욌뒗媛",
        f"- {selected.why_fit_student}",
        f"- 湲곕줉 ?곌껐: {selected.link_to_record_flow}",
    ]
    if selected.link_to_target_major_or_university:
        lines.append(f"- 紐⑺몴 ?곌껐: {selected.link_to_target_major_or_university}")

    lines.extend(
        [
            "",
            "## 利앷굅-?덉쟾 ?묒꽦 寃쎄퀎",
            "- ?뺤씤???숈깮 湲곕줉 踰붿쐞瑜??섎뒗 ?⑥젙? ?섏? ?딆뒿?덈떎.",
            "- 誘명솗???댁슜? 諛섎뱶??'異붽? ?뺤씤 ?꾩슂' ?먮뒗 '援ъ껜 ?щ? 蹂닿컯 ?꾩슂'濡??쒓린?⑸땲??",
        ]
    )
    if limited_note:
        lines.append(f"- ?쒗븳 留λ씫 ?덈궡: {limited_note}")

    lines.extend(["", "## 沅뚯옣 媛쒖슂? ?뱀뀡蹂??묒꽦 ?섎룄"])
    for section in outline:
        lines.append(f"### {section.title}")
        lines.append(section.purpose)

    lines.extend(["", "## 吏湲??덉쟾?섍쾶 二쇱옣 媛?ν븳 ?ъ떎"])
    if safe_claims:
        for claim in safe_claims[:4]:
            lines.append(f"- {claim}")
    else:
        lines.append("- 異붽? ?뺤씤 ?꾩슂")

    lines.extend(["", "## 異붽? ?뺤씤 ?꾩슂 / 援ъ껜 ?щ? 蹂닿컯 ?꾩슂"])
    for gap in unresolved:
        lines.append(f"- {gap}")

    lines.extend(
        [
            "",
            "## ?꾩엯 臾몃떒(珥덉븞)",
            (
                f"蹂?蹂닿퀬?쒕뒗 '{selected.title}'瑜?以묒떖?쇰줈, ?꾩옱源뚯? ?뺤씤 媛?ν븳 ?숈깮 湲곕줉怨?臾몄꽌 洹쇨굅瑜??좊?濡?"
                "?먭뎄??諛⑺뼢怨??섎?瑜??뺣━?쒕떎. ?곗꽑 ?뺤씤???ъ떎??諛뷀깢?쇰줈 二쇱젣 ?좎젙????뱀꽦???ㅻ챸?섍퀬, "
                "洹쇨굅媛 遺議깊븳 ??ぉ? '異붽? ?뺤씤 ?꾩슂'濡?遺꾨━??怨쇱옣 ?놁씠 ?뺤옣 媛?ν븳 ?묒꽦 援ъ“瑜??쒖떆?쒕떎."
            ),
            "",
            "## Evidence Memo",
            "- ?몃? ?먮즺??鍮꾧탳/?댁꽍 蹂댁“濡쒕쭔 ?ъ슜?섍퀬 ?숈깮 ?섑뻾 ?ъ떎濡??꾪솚?섏? ?딆뒿?덈떎.",
            "- 臾몄옣 ?뺤젙 ??異쒖쿂/湲곕줉 ?쇱튂 ?щ?瑜??뺤씤?⑸땲??",
            "",
            "## 理쒖쥌?????뺤씤 吏덈Ц",
            "- 以묒떖 吏덈Ц??蹂닿퀬???꾩껜 臾몃떒???쇨??섍쾶 諛섏쁺?섎뒗媛?",
            "- 媛??⑤씫??洹쇨굅 異쒖쿂媛 紐낆떆?섎뒗媛?",
            "- 誘명솗??二쇱옣??'異붽? ?뺤씤 ?꾩슂' ?쒓린媛 ?⑥븘?덈뒗媛?",
        ]
    )

    return "\n".join(lines).strip()


def _build_state_summary(
    *,
    context: GuidedChatContext,
    subject: str | None,
    selected_topic_id: str | None,
    suggestions: list[TopicSuggestion],
    outline: list[OutlineSection],
    starter_draft_markdown: str | None,
) -> dict[str, object]:
    selected_title = next((item.title for item in suggestions if item.id == selected_topic_id), None)
    confirmed_points = []
    if context.record_flow_summary:
        confirmed_points.append(_clip_line(context.record_flow_summary, "", 160))
    return {
        "subject": subject,
        "selected_topic": selected_title,
        "selected_topic_id": selected_topic_id,
        "thesis_question": selected_title,
        "accepted_outline": [item.title for item in outline],
        "confirmed_evidence_points": confirmed_points,
        "unresolved_evidence_gaps": context.evidence_gaps[:6],
        "draft_intent": context.project_discussion_log[-1] if context.project_discussion_log else None,
        "user_preferences": context.workshop_history[-2:],
        "starter_draft_markdown": starter_draft_markdown,
    }


def _normalize_subject(subject: str) -> str:
    clean = " ".join(subject.strip().split())
    return clean or "?먭뎄"


def _fallback_fit_message(context: GuidedChatContext, subject: str) -> str:
    if context.record_flow_summary:
        return f"湲곗〈 湲곕줉 ?먮쫫??諛뷀깢?쇰줈 {subject} 二쇱젣瑜??덉쟾?섍쾶 ?뺤옣?????덉뒿?덈떎."
    return f"?꾩옱 ?뺣낫 踰붿쐞 ?덉뿉??{subject} 二쇱젣瑜?蹂댁닔?곸쑝濡?援ъ꽦?섍린???곹빀?⑸땲??"


def _fallback_record_link(context: GuidedChatContext) -> str:
    if context.record_flow_summary:
        return f"?뺤씤??湲곕줉 ?붿빟: {_clip_line(context.record_flow_summary, '湲곕줉 ?붿빟??議댁옱?⑸땲??')}"
    return "?숈깮遺 臾몄꽌 洹쇨굅媛 ?쒗븳?곸씠?댁꽌 ?뺤씤 媛?ν븳 踰붿쐞留??ъ슜?⑸땲??"


def _fallback_target_link(context: GuidedChatContext) -> str | None:
    major = context.known_target_info.get("target_major")
    university = context.known_target_info.get("target_university")
    if major and university:
        return f"{university} {major} 諛⑺뼢怨??곌껐 媛?ν븳 二쇱젣濡??ㅺ퀎?덉뒿?덈떎."
    if major:
        return f"{major} 紐⑺몴 諛⑺뼢??諛섏쁺??二쇱젣?낅땲??"
    if university:
        return f"{university} 吏??諛⑺뼢??怨좊젮??援ъ꽦?덉뒿?덈떎."
    return None


def _fallback_novelty_message(subject: str, index: int) -> str:
    if index == 1:
        return f"{subject} 二쇱젣?먯꽌 湲곗〈 ?쒕룞??留λ씫??援ъ“?곸쑝濡??ㅻ챸?⑸땲??"
    if index == 2:
        return f"{subject} 二쇱젣?먯꽌 鍮꾧탳/寃利??④퀎瑜??ы븿?⑸땲??"
    return f"{subject} 二쇱젣?먯꽌 ?꾩냽 ?먭뎄 吏덈Ц??紐낆떆?⑸땲??"


def _fallback_caution(context: GuidedChatContext) -> str | None:
    if context.evidence_gaps:
        return "誘명솗???ъ떎???⑥젙?섏? 留먭퀬 遺議?洹쇨굅瑜?遺꾨━ ?쒓린?섏꽭??"
    return None


def _evidence_gap_note(context: GuidedChatContext) -> str | None:
    if context.evidence_gaps:
        return LIMITED_CONTEXT_NOTE
    return None


def _clip_line(value: str | None, fallback: str, limit: int = 160) -> str:
    text = " ".join((value or "").split()).strip()
    if not text:
        return fallback
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split()).strip()
    return text or None

