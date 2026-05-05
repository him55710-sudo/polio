from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field


_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "that",
    "this",
    "student",
    "report",
    "research",
    "activity",
}


@dataclass(frozen=True)
class StudentRecordAnalysis:
    """Privacy-light summary for topic generation.

    The analyzer intentionally keeps derived signals only. It should not persist
    or return the full student-record source text.
    """

    keywords: list[str] = field(default_factory=list)
    capability_signals: list[str] = field(default_factory=list)
    major_signals: list[str] = field(default_factory=list)
    gap_signals: list[str] = field(default_factory=list)


def analyze_student_record_summary(summary: str | None, *, target_major: str | None = None) -> StudentRecordAnalysis:
    text = (summary or "").strip()
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", text)
        if token.lower() not in _STOPWORDS
    ]
    counter = Counter(tokens)
    keywords = [word for word, _ in counter.most_common(18)]

    capability_signals = _collect_signals(
        text,
        {
            "analysis": ["분석", "data", "데이터", "통계", "시각화"],
            "experiment": ["실험", "측정", "변수", "검증", "simulation", "시뮬레이션"],
            "problem_solving": ["개선", "해결", "설계", "제작", "모형"],
            "communication": ["발표", "토론", "보고서", "논문", "글쓰기"],
        },
    )
    major_signals = _collect_signals(
        " ".join([text, target_major or ""]),
        {
            "architecture_city": ["건축", "도시", "구조", "재료", "교통", "환경"],
            "energy_environment": ["에너지", "기후", "탄소", "열섬", "친환경"],
            "ai_data": ["AI", "인공지능", "데이터", "모델", "알고리즘"],
            "bio_medical": ["생명", "의학", "바이오", "보건"],
        },
    )
    gap_signals = _collect_signals(
        text,
        {
            "needs_evidence": ["관심", "흥미", "느꼈다"],
            "needs_method": ["탐구", "조사"],
            "needs_depth": ["기초", "개념"],
        },
    )

    return StudentRecordAnalysis(
        keywords=keywords,
        capability_signals=capability_signals,
        major_signals=major_signals,
        gap_signals=gap_signals,
    )


def _collect_signals(text: str, groups: dict[str, list[str]]) -> list[str]:
    lowered = text.lower()
    result: list[str] = []
    for label, needles in groups.items():
        if any(needle.lower() in lowered for needle in needles):
            result.append(label)
    return result
