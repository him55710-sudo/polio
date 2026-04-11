from __future__ import annotations

import json
from typing import Any

from unifoli_api.schemas.guided_chat import GuidedChatStatePayload
from unifoli_api.db.models.workshop import WorkshopSession


def _clip(value: str | None, limit: int = 220) -> str:
    normalized = " ".join((value or "").split()).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _latest_user_message(session: WorkshopSession) -> str | None:
    for turn in reversed(session.turns or []):
        if getattr(turn, "speaker_role", "") == "user" and (turn.query or "").strip():
            return turn.query
    return None


def _infer_thesis_question(session: WorkshopSession, guided_state: GuidedChatStatePayload | None) -> str | None:
    if guided_state:
        candidate = str(guided_state.state_summary.get("thesis_question") or "").strip()
        if candidate:
            return _clip(candidate, 180)

    for turn in reversed(session.turns or []):
        if getattr(turn, "speaker_role", "") != "user":
            continue
        text = (turn.query or "").strip()
        if not text:
            continue
        if "?" in text or "ì§ˆë¬¸" in text or "?êµ¬" in text:
            return _clip(text, 180)
    return None


def _collect_user_preferences(session: WorkshopSession) -> list[str]:
    keywords = ("??, "ë¬¸ì²´", "ë¶„ëŸ‰", "ê¸¸ì´", "?•ì‹", "êµ¬ì„±", "?œí˜„")
    preferences: list[str] = []
    for turn in reversed(session.turns or []):
        if getattr(turn, "speaker_role", "") != "user":
            continue
        query = (turn.query or "").strip()
        if not query:
            continue
        if any(key in query for key in keywords):
            preferences.append(_clip(query, 140))
        if len(preferences) >= 4:
            break
    return list(reversed(preferences))


def _collect_confirmed_evidence_points(session: WorkshopSession) -> list[str]:
    points: list[str] = []

    for ref in session.pinned_references or []:
        text = _clip(getattr(ref, "text_content", None), 160)
        if text:
            points.append(f"ê³ ì • ì°¸ê³ ?ë£Œ: {text}")
        if len(points) >= 4:
            return points

    for turn in reversed(session.turns or []):
        if getattr(turn, "speaker_role", "") != "user":
            continue
        query = (turn.query or "").strip()
        if not query:
            continue
        if "ê·¼ê±°" in query or "ê¸°ë¡" in query or "ë¬¸ì„œ" in query:
            points.append(_clip(query, 160))
        if len(points) >= 4:
            break

    return list(reversed(points))


def _collect_unresolved_gaps(session: WorkshopSession, guided_state: GuidedChatStatePayload | None) -> list[str]:
    gaps: list[str] = []

    if guided_state:
        raw = guided_state.state_summary.get("unresolved_evidence_gaps")
        if isinstance(raw, list):
            for item in raw:
                text = _clip(str(item), 160)
                if text:
                    gaps.append(text)

    for turn in reversed(session.turns or []):
        content = (turn.query or "") if getattr(turn, "speaker_role", "") == "user" else (turn.response or "")
        text = (content or "").strip()
        if not text:
            continue
        if "ì¶”ê? ?•ì¸ ?„ìš”" in text or "ë³´ê°• ?„ìš”" in text:
            gaps.append(_clip(text, 160))
        if len(gaps) >= 4:
            break

    deduped: list[str] = []
    seen: set[str] = set()
    for item in gaps:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:4]


def build_workshop_memory_summary(
    session: WorkshopSession,
    *,
    guided_state: GuidedChatStatePayload | None = None,
) -> dict[str, Any]:
    selected_topic = None
    accepted_outline: list[str] = []
    if guided_state:
        selected_topic = next(
            (
                item.title
                for item in guided_state.suggestions
                if item.id == guided_state.selected_topic_id and item.title
            ),
            None,
        )
        accepted_outline = [section.title for section in guided_state.recommended_outline if section.title][:8]

    draft_intent = _latest_user_message(session)

    summary = {
        "subject": guided_state.subject if guided_state else None,
        "selected_topic": selected_topic,
        "thesis_question": _infer_thesis_question(session, guided_state),
        "accepted_outline": accepted_outline,
        "confirmed_evidence_points": _collect_confirmed_evidence_points(session),
        "unresolved_evidence_gaps": _collect_unresolved_gaps(session, guided_state),
        "draft_intent": _clip(draft_intent, 180) if draft_intent else None,
        "user_preferences": _collect_user_preferences(session),
        "starter_draft_markdown": guided_state.starter_draft_markdown if guided_state else None,
    }

    return summary


def build_workshop_memory_payload(
    session: WorkshopSession,
    project: Any,
    quest: Any,
    *,
    max_recent_turns: int = 6,
    guided_state: GuidedChatStatePayload | None = None,
) -> tuple[str, dict[str, Any]]:
    summary = build_workshop_memory_summary(session, guided_state=guided_state)

    blocks: list[str] = []
    goal_lines = [
        f"ëª©í‘œ ?€?? {getattr(project, 'target_university', None) or 'ë¯¸ì •'}",
        f"ëª©í‘œ ?„ê³µ: {getattr(project, 'target_major', None) or 'ë¯¸ì •'}",
    ]
    if quest and getattr(quest, "title", None):
        goal_lines.append(f"ëª©í‘œ ?°ì¶œë¬? {quest.title}")
    blocks.append("[?„ë¡œ?íŠ¸/?¸ì…˜ ëª©í‘œ]\n" + "\n".join(goal_lines))

    blocks.append("[ê°€?´ë“œ???œëž˜?„íŒ… ?íƒœ]\n" + json.dumps(summary, ensure_ascii=False, indent=2))

    valid_turns = [turn for turn in session.turns or [] if (turn.query or "").strip()]
    if not valid_turns:
        blocks.append("[ìµœê·¼ ?€??\n?„ì§ ?€?”ê? ?†ìŠµ?ˆë‹¤.")
        return "\n\n".join(blocks), summary

    recent_turns = valid_turns[-max_recent_turns:]
    older_count = max(0, len(valid_turns) - len(recent_turns))
    if older_count:
        blocks.append(f"[?´ì „ ?€???”ì•½]\nì´?{older_count}ê°œì˜ ?´ì „ ?´ì´ ì§„í–‰?˜ì—ˆ?µë‹ˆ?? (?ëžµ??")

    turn_lines = ["[ìµœê·¼ ?€??"]
    for turn in recent_turns:
        role = getattr(turn, "speaker_role", "user")
        if role == "assistant":
            content = (turn.response or turn.query or "").strip()
            if content:
                turn_lines.append(f"Assistant: {_clip(content, 220)}")
        else:
            turn_lines.append(f"Student: {_clip(turn.query, 220)}")

    blocks.append("\n".join(turn_lines))
    return "\n\n".join(blocks), summary


def build_workshop_memory_context(
    session: WorkshopSession,
    project: Any,
    quest: Any,
    max_recent_turns: int = 6,
    guided_state: GuidedChatStatePayload | None = None,
) -> str:
    context, _ = build_workshop_memory_payload(
        session,
        project,
        quest,
        max_recent_turns=max_recent_turns,
        guided_state=guided_state,
    )
    return context
