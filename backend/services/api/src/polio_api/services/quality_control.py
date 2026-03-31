# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from polio_domain.enums import QualityLevel, TurnType

from polio_api.services.prompt_registry import get_prompt_registry


@dataclass(frozen=True)
class QualityControlProfile:
    level: str
    label: str
    emoji: str
    color: str
    description: str
    detail: str
    student_fit: str
    safety_posture: str
    authenticity_policy: str
    hallucination_guardrail: str
    starter_mode: str
    followup_mode: str
    reference_policy: str
    reference_intensity: str
    render_depth: str
    expression_policy: str
    advanced_features_allowed: bool
    max_output_chars: int
    temperature: float
    minimum_turn_count: int
    minimum_reference_count: int
    render_threshold: int


QUALITY_CONTROL_SCHEMA_VERSION = "2026-03-23"
QUALITY_PROFILE_ASSET_NAME = "system.guardrails.workshop-quality-profiles"
WORKSHOP_CHOICE_COPY_ASSET_NAME = "chat.workshop-choice-copy"
QUALITY_LEVEL_ORDER = (
    QualityLevel.LOW.value,
    QualityLevel.MID.value,
    QualityLevel.HIGH.value,
)


def _load_prompt_json_asset(prompt_name: str) -> dict[str, object]:
    asset = get_prompt_registry().get_asset(prompt_name)
    payload = json.loads(asset.body)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Prompt asset '{prompt_name}' must contain a JSON object body.")
    return payload


@lru_cache(maxsize=1)
def _load_quality_profile_bundle() -> dict[str, object]:
    return _load_prompt_json_asset(QUALITY_PROFILE_ASSET_NAME)


@lru_cache(maxsize=1)
def _load_workshop_choice_bundle() -> dict[str, object]:
    return _load_prompt_json_asset(WORKSHOP_CHOICE_COPY_ASSET_NAME)


def _coerce_object(value: object, *, prompt_name: str, key: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(
            f"Prompt asset '{prompt_name}' key '{key}' must contain a JSON object."
        )
    return value


def _coerce_list(value: object, *, prompt_name: str, key: str) -> list[object]:
    if not isinstance(value, list):
        raise RuntimeError(
            f"Prompt asset '{prompt_name}' key '{key}' must contain a JSON array."
        )
    return value


def _build_quality_profile(level: str, raw: dict[str, object]) -> QualityControlProfile:
    declared_level = str(raw.get("level", level))
    if declared_level != level:
        raise RuntimeError(
            f"Prompt asset '{QUALITY_PROFILE_ASSET_NAME}' has mismatched level '{declared_level}' for key '{level}'."
        )

    try:
        return QualityControlProfile(
            level=declared_level,
            label=str(raw["label"]),
            emoji=str(raw["emoji"]),
            color=str(raw["color"]),
            description=str(raw["description"]),
            detail=str(raw["detail"]),
            student_fit=str(raw["student_fit"]),
            safety_posture=str(raw["safety_posture"]),
            authenticity_policy=str(raw["authenticity_policy"]),
            hallucination_guardrail=str(raw["hallucination_guardrail"]),
            starter_mode=str(raw["starter_mode"]),
            followup_mode=str(raw["followup_mode"]),
            reference_policy=str(raw["reference_policy"]),
            reference_intensity=str(raw["reference_intensity"]),
            render_depth=str(raw["render_depth"]),
            expression_policy=str(raw["expression_policy"]),
            advanced_features_allowed=bool(raw["advanced_features_allowed"]),
            max_output_chars=int(raw["max_output_chars"]),
            temperature=float(raw["temperature"]),
            minimum_turn_count=int(raw["minimum_turn_count"]),
            minimum_reference_count=int(raw["minimum_reference_count"]),
            render_threshold=int(raw["render_threshold"]),
        )
    except KeyError as exc:
        raise RuntimeError(
            f"Prompt asset '{QUALITY_PROFILE_ASSET_NAME}' is missing field '{exc.args[0]}' for level '{level}'."
        ) from exc


@lru_cache(maxsize=1)
def _get_quality_profiles() -> dict[str, QualityControlProfile]:
    bundle = _load_quality_profile_bundle()
    raw_profiles = _coerce_object(
        bundle.get("profiles"),
        prompt_name=QUALITY_PROFILE_ASSET_NAME,
        key="profiles",
    )
    profiles: dict[str, QualityControlProfile] = {}
    for level in QUALITY_LEVEL_ORDER:
        raw_profile = _coerce_object(
            raw_profiles.get(level),
            prompt_name=QUALITY_PROFILE_ASSET_NAME,
            key=f"profiles.{level}",
        )
        profiles[level] = _build_quality_profile(level, raw_profile)
    return profiles


def _normalize_template_list(
    raw_templates: list[object],
    *,
    prompt_name: str,
    key: str,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(raw_templates):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"Prompt asset '{prompt_name}' key '{key}[{index}]' must contain a JSON object."
            )
        normalized.append({str(field): str(value) for field, value in item.items()})
    return normalized


def _get_choice_templates(*, section: str, level: str) -> list[dict[str, str]]:
    bundle = _load_workshop_choice_bundle()
    raw_section = _coerce_object(
        bundle.get(section),
        prompt_name=WORKSHOP_CHOICE_COPY_ASSET_NAME,
        key=section,
    )
    raw_templates = _coerce_list(
        raw_section.get(level),
        prompt_name=WORKSHOP_CHOICE_COPY_ASSET_NAME,
        key=f"{section}.{level}",
    )
    return _normalize_template_list(
        raw_templates,
        prompt_name=WORKSHOP_CHOICE_COPY_ASSET_NAME,
        key=f"{section}.{level}",
    )


def _get_acknowledgement_templates() -> dict[str, str]:
    bundle = _load_workshop_choice_bundle()
    raw_acknowledgements = _coerce_object(
        bundle.get("acknowledgements"),
        prompt_name=WORKSHOP_CHOICE_COPY_ASSET_NAME,
        key="acknowledgements",
    )
    return {str(key): str(value) for key, value in raw_acknowledgements.items()}


def normalize_quality_level(level: str | None) -> str:
    if not level:
        return QualityLevel.MID.value
    normalized = level.strip().lower()
    if normalized in _get_quality_profiles():
        return normalized
    return QualityLevel.MID.value


def get_quality_profile(level: str | None) -> QualityControlProfile:
    return _get_quality_profiles()[normalize_quality_level(level)]


def list_quality_level_info() -> list[dict[str, object]]:
    return [serialize_quality_level_info(profile) for profile in _get_quality_profiles().values()]


def serialize_quality_level_info(profile: QualityControlProfile) -> dict[str, object]:
    return {
        "level": profile.level,
        "label": profile.label,
        "emoji": profile.emoji,
        "color": profile.color,
        "description": profile.description,
        "detail": profile.detail,
        "student_fit": profile.student_fit,
        "safety_posture": profile.safety_posture,
        "authenticity_policy": profile.authenticity_policy,
        "hallucination_guardrail": profile.hallucination_guardrail,
        "starter_mode": profile.starter_mode,
        "followup_mode": profile.followup_mode,
        "reference_policy": profile.reference_policy,
        "reference_intensity": profile.reference_intensity,
        "render_depth": profile.render_depth,
        "expression_policy": profile.expression_policy,
        "advanced_features_allowed": profile.advanced_features_allowed,
        "minimum_turn_count": profile.minimum_turn_count,
        "minimum_reference_count": profile.minimum_reference_count,
        "render_threshold": profile.render_threshold,
    }


def build_render_requirements(
    *,
    quality_level: str | None,
    context_score: int,
    turn_count: int,
    reference_count: int,
) -> dict[str, object]:
    profile = get_quality_profile(quality_level)
    missing: list[str] = []
    if context_score < profile.render_threshold:
        missing.append(f"맥락 점수 {profile.render_threshold - context_score}점 부족")
    if turn_count < profile.minimum_turn_count:
        missing.append(f"대화 턴 {profile.minimum_turn_count - turn_count}개 부족")
    if reference_count < profile.minimum_reference_count:
        missing.append(f"참고자료 {profile.minimum_reference_count - reference_count}개 부족")

    return {
        "required_context_score": profile.render_threshold,
        "minimum_turn_count": profile.minimum_turn_count,
        "minimum_reference_count": profile.minimum_reference_count,
        "current_context_score": context_score,
        "current_turn_count": turn_count,
        "current_reference_count": reference_count,
        "can_render": not missing,
        "missing": missing,
    }


def build_quality_control_metadata(
    *,
    requested_level: str,
    applied_level: str,
    turn_count: int,
    reference_count: int,
    safety_score: int | None = None,
    downgraded: bool = False,
    summary: str | None = None,
    flags: dict[str, str] | None = None,
    checks: dict[str, dict[str, object]] | None = None,
    repair_applied: bool = False,
    repair_strategy: str | None = None,
    advanced_features_requested: bool = False,
    advanced_features_applied: bool = False,
    advanced_features_reason: str | None = None,
) -> dict[str, object]:
    requested_profile = get_quality_profile(requested_level)
    applied_profile = get_quality_profile(applied_level)
    return {
        "schema_version": QUALITY_CONTROL_SCHEMA_VERSION,
        "requested_level": requested_profile.level,
        "requested_label": requested_profile.label,
        "applied_level": applied_profile.level,
        "applied_label": applied_profile.label,
        "student_fit": applied_profile.student_fit,
        "safety_posture": applied_profile.safety_posture,
        "authenticity_policy": applied_profile.authenticity_policy,
        "hallucination_guardrail": applied_profile.hallucination_guardrail,
        "starter_mode": applied_profile.starter_mode,
        "followup_mode": applied_profile.followup_mode,
        "reference_policy": applied_profile.reference_policy,
        "reference_intensity": applied_profile.reference_intensity,
        "render_depth": applied_profile.render_depth,
        "expression_policy": applied_profile.expression_policy,
        "advanced_features_allowed": applied_profile.advanced_features_allowed,
        "advanced_features_requested": advanced_features_requested,
        "advanced_features_applied": advanced_features_applied,
        "advanced_features_reason": advanced_features_reason,
        "minimum_turn_count": applied_profile.minimum_turn_count,
        "minimum_reference_count": applied_profile.minimum_reference_count,
        "turn_count": turn_count,
        "reference_count": reference_count,
        "safety_score": safety_score,
        "downgraded": downgraded,
        "summary": summary,
        "flags": flags or {},
        "checks": checks or {},
        "repair_applied": repair_applied,
        "repair_strategy": repair_strategy,
    }


def resolve_advanced_features(
    *,
    requested: bool,
    quality_level: str | None,
    reference_count: int,
) -> tuple[bool, str]:
    profile = get_quality_profile(quality_level)
    if not requested:
        return False, "고급 확장은 요청되지 않았습니다."
    if not profile.advanced_features_allowed:
        return False, f"{profile.label}에서는 고급 확장을 허용하지 않습니다."
    if reference_count < profile.minimum_reference_count:
        return (
            False,
            f"{profile.label}에서는 참고자료 {profile.minimum_reference_count}개 이상이 있을 때만 고급 확장을 적용합니다.",
        )
    return True, f"{profile.label} 기준과 참고자료 조건이 충족되어 고급 확장을 적용합니다."


def build_starter_choices(
    *,
    quality_level: str | None,
    quest_title: str | None,
    target_major: str | None,
    recommended_output_type: str | None,
) -> list[dict[str, object]]:
    profile = get_quality_profile(quality_level)
    quest_label = quest_title or "이번 탐구"
    major_label = target_major or "희망 전공"
    output_label = (recommended_output_type or "탐구 결과물").lower()
    templates = _get_choice_templates(section="starter_templates", level=profile.level)

    return [
        {
            "id": template["id"],
            "label": template["label"],
            "description": template["description"],
            "payload": {
                "prompt": template["prompt_template"].format(
                    quest_label=quest_label,
                    major_label=major_label,
                    output_label=output_label,
                ),
                "quality_level": profile.level,
                "choice_kind": TurnType.STARTER.value,
            },
        }
        for template in templates
    ]


def build_followup_choices(
    *,
    quality_level: str | None,
    turn_count: int,
) -> list[dict[str, object]]:
    profile = get_quality_profile(quality_level)
    templates = _get_choice_templates(section="followup_templates", level=profile.level)

    return [
        {
            "id": template["id_template"].format(turn_count=turn_count),
            "label": template["label"],
            "description": template["description"],
            "payload": {
                "prompt": template["prompt_template"],
                "quality_level": profile.level,
                "choice_kind": TurnType.FOLLOW_UP.value,
            },
        }
        for template in templates
    ]


def build_choice_acknowledgement(*, quality_level: str | None, label: str) -> str:
    profile = get_quality_profile(quality_level)
    templates = _get_acknowledgement_templates()
    return templates["choice_template"].format(
        profile_label=profile.label,
        label=label,
        followup_mode=profile.followup_mode.lower(),
    )


def build_message_acknowledgement(*, quality_level: str | None, next_choice_label: str | None) -> str:
    profile = get_quality_profile(quality_level)
    templates = _get_acknowledgement_templates()
    guidance = (
        templates["guidance_template"].format(next_choice_label=next_choice_label)
        if next_choice_label
        else ""
    )
    return templates["message_template"].format(
        profile_label=profile.label,
        render_depth=profile.render_depth,
        guidance=guidance,
    ).strip()
