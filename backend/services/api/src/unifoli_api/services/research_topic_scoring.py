from __future__ import annotations

from dataclasses import dataclass


TOPIC_SCORE_AXES: tuple[str, ...] = (
    "connection",
    "depth",
    "career_fit",
    "creativity",
    "feasibility",
    "social_meaning",
    "admissions_appeal",
    "completion",
    "differentiation",
)

COMMON_TOPIC_PENALTY_KEYWORDS = (
    "장단점",
    "중요성",
    "필요성",
    "영향",
    "문제점",
    "미래",
)

METHOD_KEYWORDS = (
    "실험",
    "측정",
    "설문",
    "데이터",
    "시뮬레이션",
    "모형",
    "비교",
    "분석",
    "제작",
)

SOCIAL_KEYWORDS = (
    "기후",
    "도시",
    "에너지",
    "환경",
    "안전",
    "고령화",
    "AI",
    "지역",
    "탄소",
    "열섬",
)


@dataclass(frozen=True)
class TopicScoreCard:
    scores: dict[str, int]
    total_score: int
    topic_band: str
    risk_note: str


def score_topic_candidate(
    *,
    title: str,
    record_summary: str | None = None,
    target_major: str | None = None,
    method_hint: str | None = None,
    social_hint: str | None = None,
) -> TopicScoreCard:
    text = " ".join([title, record_summary or "", target_major or "", method_hint or "", social_hint or ""])
    scores = {axis: 3 for axis in TOPIC_SCORE_AXES}

    if _has_overlap(title, record_summary):
        scores["connection"] = 5
    if target_major and _has_overlap(title, target_major):
        scores["career_fit"] = 5
    if any(keyword.lower() in text.lower() for keyword in METHOD_KEYWORDS):
        scores["feasibility"] = 5
        scores["completion"] = 4
    if any(keyword.lower() in text.lower() for keyword in SOCIAL_KEYWORDS):
        scores["social_meaning"] = 5
        scores["admissions_appeal"] = 4
    if any(keyword in title for keyword in ("융합", "최적화", "모델", "비교", "설계", "데이터")):
        scores["creativity"] = 4
        scores["depth"] = 4
        scores["differentiation"] = 4

    common_penalty = any(keyword in title for keyword in COMMON_TOPIC_PENALTY_KEYWORDS)
    if common_penalty and not any(keyword in title for keyword in METHOD_KEYWORDS):
        scores["creativity"] = max(1, scores["creativity"] - 1)
        scores["feasibility"] = max(1, scores["feasibility"] - 1)
        scores["differentiation"] = max(1, scores["differentiation"] - 1)

    total_score = sum(scores.values())
    risk_note = ""
    if scores["feasibility"] <= 2:
        risk_note = "검증 방법이 약하므로 조사, 실험, 데이터 분석 중 하나를 반드시 붙이세요."
    elif common_penalty:
        risk_note = "주제가 넓어 보일 수 있으므로 변수와 측정 지표를 좁히세요."

    return TopicScoreCard(
        scores=scores,
        total_score=total_score,
        topic_band="challenging" if scores["depth"] + scores["creativity"] + scores["feasibility"] >= 13 else "safe",
        risk_note=risk_note,
    )


def _has_overlap(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    left_tokens = {token for token in left.lower().replace("/", " ").split() if len(token) >= 2}
    right_tokens = {token for token in right.lower().replace("/", " ").split() if len(token) >= 2}
    return bool(left_tokens & right_tokens)
