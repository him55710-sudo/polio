from __future__ import annotations

from typing import Literal, cast

PositiveAxisKey = Literal[
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
]

AdmissionAxisKey = Literal[
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
    "authenticity_risk",
]

POSITIVE_AXIS_KEYS: tuple[PositiveAxisKey, ...] = (
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
)

POSITIVE_AXIS_LABELS: dict[PositiveAxisKey, str] = {
    "universal_rigor": "학업 및 근거 엄밀성",
    "universal_specificity": "근거 구체성",
    "relational_narrative": "서사적 발전성",
    "relational_continuity": "탐구의 연속성",
    "cluster_depth": "전공 심층성",
    "cluster_suitability": "전공 적합성",
}

LEGACY_AXIS_KEY_ALIASES: dict[str, PositiveAxisKey] = {
    "conceptual_depth": "universal_rigor",
    "evidence_density": "universal_specificity",
    "process_explanation": "relational_narrative",
    "inquiry_continuity": "relational_continuity",
    "subject_major_alignment": "cluster_suitability",
}


def normalize_positive_axis_key(value: str | None) -> PositiveAxisKey | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    if normalized in POSITIVE_AXIS_KEYS:
        return cast(PositiveAxisKey, normalized)
    return LEGACY_AXIS_KEY_ALIASES.get(normalized)
