from __future__ import annotations

from typing import TYPE_CHECKING
import json

from polio_api.db.models.workshop import WorkshopSession

if TYPE_CHECKING:
    from polio_api.db.models.project import Project
    from polio_api.db.models.quest import Quest

def build_workshop_memory_context(
    session: WorkshopSession,
    project: Project,
    quest: Quest | None,
    max_recent_turns: int = 6
) -> str:
    """
    Builds a bounded, inspectable conversation memory block for the workshop chat model.
    """
    blocks = []

    # 1. Goal Context
    goal_lines = []
    goal_lines.append(f"목표 대학: {project.target_university or '미정'}")
    goal_lines.append(f"목표 전공: {project.target_major or '미정'}")
    if quest:
        goal_lines.append(f"목표 산출물: {quest.title}")
    
    blocks.append("[프로젝트/세션 목표]\n" + "\n".join(goal_lines))

    # 2. Pinned References
    if session.pinned_references:
        ref_lines = ["[고정된 참고 자료]"]
        for i, ref in enumerate(session.pinned_references, 1):
            source = f" (출처: {ref.source_type})" if ref.source_type else ""
            content = ref.text_content.replace('\n', ' ').strip()
            if len(content) > 300:
                content = content[:300] + "..."
            ref_lines.append(f"{i}. {content}{source}")
        blocks.append("\n".join(ref_lines))

    # 3. Turns
    valid_turns = [t for t in session.turns if t.query.strip()]
    if valid_turns:
        recent_turns = valid_turns[-max_recent_turns:]
        older_turns = valid_turns[:-max_recent_turns]

        if older_turns:
            blocks.append(f"[이전 대화 요약]\n총 {len(older_turns)}개의 이전 턴이 진행되었습니다. (생략됨)")

        chat_lines = ["[최근 대화 기록]"]
        for turn in recent_turns:
            if turn.speaker_role == "user":
                chat_lines.append(f"Student: {turn.query}")
            else:
                # For assistant logic, it might have response, or if query is from assistant somehow
                if turn.response:
                    chat_lines.append(f"Assistant: {turn.response}")
                else:
                    chat_lines.append(f"Assistant: {turn.query}")
        
        blocks.append("\n".join(chat_lines))
    else:
        blocks.append("[대화 기록]\n아직 진행된 대화가 없습니다.")

    return "\n\n".join(blocks)
