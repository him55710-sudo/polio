from __future__ import annotations

from typing import Literal, cast

PositiveAxisKey = Literal[
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
    "community_contribution",
]

AdmissionAxisKey = Literal[
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
    "community_contribution",
    "authenticity_risk",
]

POSITIVE_AXIS_KEYS: tuple[PositiveAxisKey, ...] = (
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
    "community_contribution",
)

ADMISSION_AXIS_KEYS: tuple[AdmissionAxisKey, ...] = (
    "universal_rigor",
    "universal_specificity",
    "relational_narrative",
    "relational_continuity",
    "cluster_depth",
    "cluster_suitability",
    "community_contribution",
    "authenticity_risk",
)

POSITIVE_AXIS_LABELS: dict[PositiveAxisKey, str] = {
    "universal_rigor": "학업 엄밀성",
    "universal_specificity": "근거 구체성",
    "relational_narrative": "성장/탐구 과정",
    "relational_continuity": "진로 탐색 연속성",
    "cluster_depth": "전공 탐구 깊이",
    "cluster_suitability": "전공/계열 적합성",
    "community_contribution": "공동체 기여",
}

LEGACY_AXIS_KEY_ALIASES: dict[str, PositiveAxisKey] = {
    "academic_rigor": "universal_rigor",
    "conceptual_depth": "universal_rigor",
    "evidence_density": "universal_specificity",
    "specificity_and_concreteness": "universal_specificity",
    "process_explanation": "relational_narrative",
    "growth_process": "relational_narrative",
    "inquiry_continuity": "relational_continuity",
    "subject_major_alignment": "cluster_suitability",
    "major_fit_alignment": "cluster_suitability",
    "community": "community_contribution",
    "community_competency": "community_contribution",
    "social_competency": "community_contribution",
}


def normalize_positive_axis_key(value: str | None) -> PositiveAxisKey | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    if normalized in POSITIVE_AXIS_KEYS:
        return cast(PositiveAxisKey, normalized)
    return LEGACY_AXIS_KEY_ALIASES.get(normalized)
