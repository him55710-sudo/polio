from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from unifoli_api.db.models.blueprint import Blueprint
from unifoli_api.db.models.project import Project
from unifoli_api.db.models.quest import Quest
from unifoli_api.schemas.blueprint import (
    CurrentBlueprintRead,
    QuestGroupRead,
    QuestRead,
    QuestStartResponse,
    StarterChoiceRead,
)
from unifoli_api.services.quality_control import build_starter_choices


@dataclass
class BlueprintSignals:
    headline: str
    strengths: list[str]
    gaps: list[str]
    risk_level: str
    recommended_focus: str


_SUBJECT_RULES = (
    ("수학", ("data", "graph", "stat", "ratio", "probability", "calculation")),
    ("과학", ("experiment", "measure", "sensor", "biology", "chemistry", "physics", "lab")),
    ("사회", ("policy", "economy", "society", "history", "market", "law", "community")),
    ("영어", ("english", "global", "translation", "international")),
    ("정보", ("code", "coding", "python", "ai", "algorithm", "model", "software")),
    ("국어", ("essay", "writing", "reading", "presentation", "speech", "reflection", "report")),
)


def _clean_phrase(text: str, *, max_words: int = 9) -> str:
    # Strip common English prefixes that LLMs sometimes hallucinate even when told to use Korean
    noise_patterns = [
        r"^Semester priority\s*:\s*",
        r"^Recommended focus\s*:\s*",
        r"^Priority\s*:\s*",
        r"^Focus\s*:\s*",
        r"^Task\s*:\s*",
        r"^Quest\s*:\s*",
    ]
    normalized = text.strip()
    for pattern in noise_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

    normalized = re.sub(r"\s+", " ", normalized).strip(" .,-")
    if not normalized:
        return "다음 기록 보완 과제"

    words = normalized.split(" ")
    clipped = " ".join(words[:max_words]).strip()
    return clipped[:90].rstrip(" ,.-")


def _infer_subject(text: str, target_major: str | None) -> str:
    lowered = f"{text} {target_major or ''}".lower()
    for subject, keywords in _SUBJECT_RULES:
        if any(keyword in lowered for keyword in keywords):
            return subject
    return target_major or "진로 탐색"


def _infer_output_type(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("measure", "compare", "data", "graph", "analysis", "trend")):
        return "데이터 비교 분석 보고서"
    if any(keyword in lowered for keyword in ("experiment", "lab", "test", "sensor")):
        return "실험/실습 로그"
    if any(keyword in lowered for keyword in ("survey", "interview", "community", "stakeholder")):
        return "인터뷰/설문 조사 요약"
    if any(keyword in lowered for keyword in ("reflection", "feedback", "limit", "improve")):
        return "성찰 및 피드백 메모"
    if any(keyword in lowered for keyword in ("reading", "paper", "article", "source")):
        return "문헌 탐구 및 자료 분석 노트"
    return "탐구 보고서"


def _difficulty_for(index: int, risk_level: str, priority: bool) -> str:
    if risk_level == "danger":
        return "high" if index == 0 or priority else "medium"
    if risk_level == "warning":
        return "medium" if index < 2 or priority else "low"
    return "medium" if priority else "low"


def _build_title(subject: str, focus: str, priority: bool) -> str:
    focus_phrase = _clean_phrase(focus, max_words=8)
    prefix = "학기 핵심 과제" if priority else f"{subject} 탐구 퀘스트"
    return f"{prefix}: {focus_phrase}"


def _build_summary(focus: str, output_type: str) -> str:
    return (
        f"진단된 공백을 메우기 위해 {_clean_phrase(focus, max_words=12)}에 관한 "
        f"실질적인 증거를 생성하는 {output_type}를 작성해 보세요."
    )


def _build_why_this_matters(focus: str, target_major: str | None, strongest_signal: str | None) -> str:
    major_label = target_major or "목표 전공"
    strongest = strongest_signal or "현재 기록된 최고의 강점"
    return (
        f"{_clean_phrase(focus, max_words=12)}와 관련된 가시적인 공백을 보완하고 이를 {major_label}과 연결합니다. "
        f"또한 {strongest}을 바탕으로 하여 흐름이 끊기지 않는 심화 탐구를 이어갈 수 있습니다."
    )


def _build_expected_record_impact(output_type: str, subject: str, target_major: str | None) -> str:
    major_label = target_major or subject
    return (
        f"{subject} 교과에서 명확한 {output_type} 흔적을 남겨, "
        f"생기부가 {major_label} 전공 적합성을 잘 보여주는 증거가 될 수 있도록 합니다."
    )


def _ordered_quests(blueprint: Blueprint) -> list[Quest]:
    difficulty_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        blueprint.quests,
        key=lambda quest: (
            difficulty_rank.get(quest.difficulty, 9),
            quest.created_at,
            quest.title,
        ),
    )


def _quest_to_read(quest: Quest) -> QuestRead:
    return QuestRead(
        id=quest.id,
        subject=quest.subject,
        title=quest.title,
        summary=quest.summary,
        difficulty=quest.difficulty,
        why_this_matters=quest.why_this_matters,
        expected_record_impact=quest.expected_record_impact,
        recommended_output_type=quest.recommended_output_type,
        status=quest.status,
    )


def _group_quests(quests: list[Quest], *, key: str) -> list[QuestGroupRead]:
    grouped: OrderedDict[str, list[QuestRead]] = OrderedDict()
    for quest in quests:
        group_name = getattr(quest, key)
        grouped.setdefault(group_name, []).append(_quest_to_read(quest))
    return [QuestGroupRead(name=name, quests=items) for name, items in grouped.items()]


def _build_starter_choices(quest: Quest, project: Project | None) -> list[StarterChoiceRead]:
    starter_payload = build_starter_choices(
        quality_level="mid",
        quest_title=quest.title,
        target_major=project.target_major if project else None,
        recommended_output_type=quest.recommended_output_type,
    )
    return [
        StarterChoiceRead(
            id=item["id"],
            label=item["label"],
            prompt=str((item.get("payload") or {}).get("prompt") or item["label"]),
        )
        for item in starter_payload
    ]


def _build_document_seed_markdown(quest: Quest, project: Project | None) -> str:
    major_label = project.target_major if project and project.target_major else quest.subject
    return "\n".join(
        [
            f"# {quest.title}",
            "",
            "## 이 퀘스트를 수행해야 하는 이유",
            quest.why_this_matters,
            "",
            "## 기대되는 생기부 변화",
            quest.expected_record_impact,
            "",
            "## 증거 생성 계획",
            f"- 교과 연계: {quest.subject}",
            f"- 희망 전공 연결: {major_label}",
            f"- 산출물 형식: {quest.recommended_output_type}",
            "- 수집할 증거 목록:",
            "  - 관찰 기록 또는 참고 자료 1",
            "  - 관찰 기록 또는 참고 자료 2",
            "  - 비교 분석 또는 성찰 포인트",
            "",
            "## 초안 작성 노트",
            "- 구체적인 탐구 질문은 무엇인가요?",
            "- 이번 학기에 수집할 수 있는 증거는 무엇인가요?",
            "- 무엇을 배웠고, 어떤 한계가 있었나요?",
        ]
    ).strip()


def build_blueprint_signals(
    *,
    headline: str,
    strengths: list[str] | None,
    gaps: list[str] | None,
    risk_level: str,
    recommended_focus: str,
) -> BlueprintSignals:
    normalized_strengths = [item.strip() for item in strengths or [] if item and item.strip()]
    normalized_gaps = [item.strip() for item in gaps or [] if item and item.strip()]

    if not normalized_gaps and recommended_focus.strip():
        normalized_gaps.append(recommended_focus.strip())
    if not normalized_strengths:
        normalized_strengths.append("학생부에 기록된 기존 탐구 성과와 강점")

    focus_text = recommended_focus.strip() or (normalized_gaps[0] if normalized_gaps else "진단 내용을 바탕으로 실질적인 역량 보완 탐구를 시작하세요.")
    headline_text = headline.strip() or "다음 단계는 진단 내용을 바탕으로 실질적인 기록 보완 탐구를 시작하는 것입니다."

    return BlueprintSignals(
        headline=headline_text,
        strengths=normalized_strengths[:3],
        gaps=normalized_gaps[:4],
        risk_level=risk_level,
        recommended_focus=focus_text,
    )


def create_blueprint_from_signals(
    db: Session,
    *,
    project: Project,
    signals: BlueprintSignals,
    diagnosis_run_id: str | None = None,
) -> Blueprint:
    blueprint = Blueprint(
        project_id=project.id,
        diagnosis_run_id=diagnosis_run_id,
        headline=signals.headline,
        recommended_focus=signals.recommended_focus,
    )
    db.add(blueprint)
    db.flush()

    strongest_signal = signals.strengths[0] if signals.strengths else None
    queue: list[tuple[str, bool]] = []
    seen: set[str] = set()

    for index, focus in enumerate([signals.recommended_focus, *signals.gaps]):
        normalized = focus.strip()
        if not normalized:
            continue
        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        queue.append((normalized, index == 0))
        if len(queue) >= 4:
            break

    if not queue:
        queue.append((signals.recommended_focus, True))

    for index, (focus, priority) in enumerate(queue):
        subject = _infer_subject(focus, project.target_major)
        output_type = _infer_output_type(focus)
        db.add(
            Quest(
                blueprint_id=blueprint.id,
                subject=subject,
                title=_build_title(subject, focus, priority),
                summary=_build_summary(focus, output_type),
                difficulty=_difficulty_for(index, signals.risk_level, priority),
                why_this_matters=_build_why_this_matters(focus, project.target_major, strongest_signal),
                expected_record_impact=_build_expected_record_impact(output_type, subject, project.target_major),
                recommended_output_type=output_type,
                status="PENDING",
            )
        )

    db.commit()
    return get_blueprint_by_id(db, blueprint.id)


def create_blueprint_from_project_diagnosis(
    db: Session,
    *,
    project: Project,
    headline: str,
    strengths: list[str],
    gaps: list[str],
    risk_level: str,
    recommended_focus: str,
) -> Blueprint:
    signals = build_blueprint_signals(
        headline=headline,
        strengths=strengths,
        gaps=gaps,
        risk_level=risk_level,
        recommended_focus=recommended_focus,
    )
    return create_blueprint_from_signals(db, project=project, signals=signals)


def get_blueprint_by_id(db: Session, blueprint_id: str) -> Blueprint:
    stmt = (
        select(Blueprint)
        .where(Blueprint.id == blueprint_id)
        .options(joinedload(Blueprint.project), selectinload(Blueprint.quests))
    )
    blueprint = db.scalar(stmt)
    if blueprint is None:
        raise ValueError(f"Blueprint not found: {blueprint_id}")
    return blueprint


def get_current_blueprint(
    db: Session,
    *,
    project_id: str | None = None,
    owner_user_id: str | None = None,
) -> Blueprint | None:
    stmt = select(Blueprint).options(joinedload(Blueprint.project), selectinload(Blueprint.quests))
    if owner_user_id:
        stmt = stmt.join(Blueprint.project).where(Project.owner_user_id == owner_user_id)
    if project_id:
        stmt = stmt.where(Blueprint.project_id == project_id)
    stmt = stmt.order_by(Blueprint.created_at.desc())
    return db.scalars(stmt).first()


def build_current_blueprint_read(blueprint: Blueprint) -> CurrentBlueprintRead:
    ordered_quests = _ordered_quests(blueprint)
    priority_quests = ordered_quests[:3]

    if priority_quests:
        semester_priority_message = (
            f"진단 내용을 이번 학기에 기록 가능한 증거로 만들기 위해 '{priority_quests[0].title}'부터 시작해 보세요."
        )
    else:
        semester_priority_message = "아직 실행 가능한 퀘스트가 없습니다."

    expected_record_effects: list[str] = []
    for quest in priority_quests:
        if quest.expected_record_impact not in expected_record_effects:
            expected_record_effects.append(quest.expected_record_impact)

    return CurrentBlueprintRead(
        id=blueprint.id,
        project_id=blueprint.project_id,
        project_title=blueprint.project.title if blueprint.project else "Current Project",
        target_major=blueprint.project.target_major if blueprint.project else None,
        headline=blueprint.headline or "Action blueprint ready.",
        recommended_focus=blueprint.recommended_focus or (priority_quests[0].summary if priority_quests else ""),
        semester_priority_message=semester_priority_message,
        priority_quests=[_quest_to_read(quest) for quest in priority_quests],
        subject_groups=_group_quests(ordered_quests, key="subject"),
        activity_groups=_group_quests(ordered_quests, key="recommended_output_type"),
        expected_record_effects=expected_record_effects,
        created_at=blueprint.created_at,
    )


def start_quest(db: Session, quest: Quest) -> QuestStartResponse:
    quest.status = "IN_PROGRESS"
    db.add(quest)
    db.commit()
    db.refresh(quest)

    blueprint = get_blueprint_by_id(db, quest.blueprint_id)
    project = blueprint.project
    starter_choices = _build_starter_choices(quest, project)
    major_label = project.target_major if project and project.target_major else quest.subject
    workshop_intro = (
        f"퀘스트 시작: {quest.title}. 이번 학기에 {major_label} 역량을 강화할 수 있는 "
        f"실질적인 {quest.recommended_output_type}에 집중해 보세요."
    )

    return QuestStartResponse(
        quest_id=quest.id,
        blueprint_id=quest.blueprint_id,
        project_id=blueprint.project_id,
        project_title=project.title if project else "Current Project",
        target_major=project.target_major if project else None,
        subject=quest.subject,
        title=quest.title,
        summary=quest.summary,
        why_this_matters=quest.why_this_matters,
        expected_record_impact=quest.expected_record_impact,
        recommended_output_type=quest.recommended_output_type,
        status=quest.status,
        workshop_intro=workshop_intro,
        document_seed_markdown=_build_document_seed_markdown(quest, project),
        starter_choices_seed=starter_choices,
    )
