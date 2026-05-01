from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from unifoli_api.services.diagnosis_axis_schema import ADMISSION_AXIS_KEYS, AdmissionAxisKey


@dataclass(frozen=True, slots=True)
class AdmissionsCriteriaSource:
    id: str
    title: str
    publisher: str
    url: str
    source_type: str
    summary: str
    school_year: int | None = None
    basis_year: int | None = None
    university_aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AdmissionsCriterion:
    id: str
    group: str
    label: str
    axis_keys: tuple[AdmissionAxisKey, ...]
    source_ids: tuple[str, ...]
    summary: str
    evidence_excerpt: str
    input_factors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdmissionsCriteriaProfile:
    source_ids: tuple[str, ...]
    criteria: tuple[AdmissionsCriterion, ...]
    target_university_matched: bool
    target_source_ids: tuple[str, ...]


_RESOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "admissions_criteria_2026.json"
)


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "")


def _as_tuple(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(str(item).strip() for item in values if str(item).strip())


@lru_cache(maxsize=1)
def load_admissions_criteria_corpus() -> dict[str, Any]:
    return json.loads(_RESOURCE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_admissions_criteria_sources() -> dict[str, AdmissionsCriteriaSource]:
    raw = load_admissions_criteria_corpus()
    sources: dict[str, AdmissionsCriteriaSource] = {}
    for item in raw.get("sources", []):
        if not isinstance(item, dict):
            continue
        source = AdmissionsCriteriaSource(
            id=str(item.get("id") or "").strip(),
            title=str(item.get("title") or "").strip(),
            publisher=str(item.get("publisher") or "").strip(),
            url=str(item.get("url") or "").strip(),
            source_type=str(item.get("source_type") or "").strip(),
            summary=str(item.get("summary") or "").strip(),
            school_year=_coerce_int(item.get("school_year")),
            basis_year=_coerce_int(item.get("basis_year")),
            university_aliases=_as_tuple(item.get("university_aliases")),
        )
        if source.id:
            sources[source.id] = source
    return sources


@lru_cache(maxsize=1)
def load_admissions_criteria() -> tuple[AdmissionsCriterion, ...]:
    raw = load_admissions_criteria_corpus()
    criteria: list[AdmissionsCriterion] = []
    for item in raw.get("criteria", []):
        if not isinstance(item, dict):
            continue
        axis_keys = tuple(
            str(axis).strip()
            for axis in item.get("axis_keys", [])
            if str(axis).strip()
        )
        criteria.append(
            AdmissionsCriterion(
                id=str(item.get("id") or "").strip(),
                group=str(item.get("group") or "").strip(),
                label=str(item.get("label") or "").strip(),
                axis_keys=axis_keys,  # type: ignore[arg-type]
                source_ids=_as_tuple(item.get("source_ids")),
                summary=str(item.get("summary") or "").strip(),
                evidence_excerpt=str(item.get("evidence_excerpt") or "").strip(),
                input_factors=_as_tuple(item.get("input_factors")),
            )
        )
    return tuple(item for item in criteria if item.id)


def resolve_admissions_criteria_profile(
    *,
    target_university: str | None,
    interest_universities: list[str] | None = None,
) -> AdmissionsCriteriaProfile:
    sources = load_admissions_criteria_sources()
    criteria = load_admissions_criteria()
    targets = [_normalize_text(target_university), *[_normalize_text(item) for item in interest_universities or []]]
    targets = [item for item in targets if item]

    target_source_ids: list[str] = []
    for source in sources.values():
        aliases = [_normalize_text(alias) for alias in source.university_aliases]
        if aliases and any(alias and any(alias in target for target in targets) for alias in aliases):
            target_source_ids.append(source.id)

    baseline_ids = {
        "kcue_2026_basic",
        "common_elements_2022",
    }
    selected_source_ids: set[str] = set(baseline_ids)
    selected_source_ids.update(target_source_ids)

    selected_criteria = tuple(
        criterion
        for criterion in criteria
        if any(source_id in selected_source_ids for source_id in criterion.source_ids)
    )
    selected_source_ids.update(
        source_id
        for criterion in selected_criteria
        for source_id in criterion.source_ids
        if source_id in sources
        and (source_id in baseline_ids or source_id in target_source_ids)
    )

    return AdmissionsCriteriaProfile(
        source_ids=tuple(sorted(selected_source_ids)),
        criteria=selected_criteria,
        target_university_matched=bool(target_source_ids),
        target_source_ids=tuple(sorted(target_source_ids)),
    )


def criteria_for_axis(
    profile: AdmissionsCriteriaProfile,
    axis_key: AdmissionAxisKey,
) -> tuple[AdmissionsCriterion, ...]:
    return tuple(criterion for criterion in profile.criteria if axis_key in criterion.axis_keys)


def criteria_refs_for_axis(
    profile: AdmissionsCriteriaProfile,
    axis_key: AdmissionAxisKey,
) -> list[str]:
    refs: list[str] = []
    for criterion in criteria_for_axis(profile, axis_key):
        for source_id in criterion.source_ids:
            if source_id in profile.source_ids and source_id not in refs:
                refs.append(source_id)
    if refs:
        return refs
    return [source_id for source_id in ("kcue_2026_basic", "common_elements_2022") if source_id in profile.source_ids]


def input_factors_for_axis(
    profile: AdmissionsCriteriaProfile,
    axis_key: AdmissionAxisKey,
) -> list[str]:
    factors: list[str] = []
    for criterion in criteria_for_axis(profile, axis_key):
        for factor in criterion.input_factors:
            if factor not in factors:
                factors.append(factor)
    return factors


def confidence_note_for_axis(
    profile: AdmissionsCriteriaProfile,
    axis_key: AdmissionAxisKey,
) -> str:
    target_note = (
        "목표 대학의 2026 학종 자료를 함께 반영했습니다."
        if profile.target_university_matched and axis_key != "authenticity_risk"
        else "공통 2026 학종 기준을 기본값으로 적용했습니다."
    )
    return (
        f"{target_note} 공식 기준은 평가 맥락이며, 학생 행동과 성취 판단은 업로드된 학생부 근거로만 제한합니다."
    )


def validate_admissions_criteria_corpus() -> list[str]:
    errors: list[str] = []
    raw = load_admissions_criteria_corpus()
    source_ids: set[str] = set()

    for source in raw.get("sources", []):
        if not isinstance(source, dict):
            errors.append("source entry must be an object")
            continue
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            errors.append("source id is required")
            continue
        source_ids.add(source_id)
        if not str(source.get("url") or "").strip():
            errors.append(f"{source_id}: url is required")
        if _coerce_int(source.get("school_year")) != 2026 and _coerce_int(source.get("basis_year")) is None:
            errors.append(f"{source_id}: expected school_year=2026 or basis_year")

    for criterion in raw.get("criteria", []):
        if not isinstance(criterion, dict):
            errors.append("criterion entry must be an object")
            continue
        criterion_id = str(criterion.get("id") or "").strip()
        if not criterion_id:
            errors.append("criterion id is required")
        refs = _as_tuple(criterion.get("source_ids"))
        if not refs:
            errors.append(f"{criterion_id}: source_ids are required")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{criterion_id}: unknown source id {ref}")
        axis_keys = _as_tuple(criterion.get("axis_keys"))
        if not axis_keys:
            errors.append(f"{criterion_id}: axis_keys are required")
        for axis_key in axis_keys:
            if axis_key not in ADMISSION_AXIS_KEYS:
                errors.append(f"{criterion_id}: unknown axis key {axis_key}")
        if not str(criterion.get("summary") or "").strip():
            errors.append(f"{criterion_id}: summary is required")

    return errors


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
