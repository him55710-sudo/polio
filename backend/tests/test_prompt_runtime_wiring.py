from __future__ import annotations

import json
from types import SimpleNamespace

from unifoli_api.api.routes.drafts import ReferenceMaterial, _build_system_instruction
from unifoli_api.services import quality_control
from unifoli_api.services.diagnosis_service import (
    _build_diagnosis_prompt,
    _build_diagnosis_system_instruction,
)
from unifoli_api.services.workshop_render_service import (
    _build_quality_guardrail,
    _build_render_prompt,
    _build_render_system_instruction,
)


def test_diagnosis_runtime_uses_registry_prompt() -> None:
    instruction = _build_diagnosis_system_instruction()
    prompt = _build_diagnosis_prompt(
        target_context="Target University: Test University\nTarget Major: Sociology",
        user_major="Sociology",
        masked_text="Measured survey responses and reflected on limits.",
    )

    assert "Polio's diagnosis engine." in instruction
    assert "Output all user-facing string fields in Korean" in instruction
    assert "[Masked Student Record]" in prompt


def test_draft_chat_system_instruction_uses_registry_prompt() -> None:
    instruction = _build_system_instruction(
        target_university="Test University",
        target_major="Education",
        reference_materials=[
            ReferenceMaterial(
                title="Student Motivation Research",
                authors=["A. Kim"],
                abstract="A short abstract about student motivation.",
                year=2024,
            )
        ],
    )

    assert "Polio's coaching-first chat layer." in instruction
    assert "Student Motivation Research" in instruction
    assert "Test University" in instruction


def test_render_runtime_uses_registry_prompt_and_provenance_instruction() -> None:
    prompt = _build_render_prompt(
        turns_text="[message] Student explored local air-quality data.",
        references_text="- [manual_note] Ministry air-quality report excerpt.",
        target_major="Environmental Engineering",
        target_university="Quality University",
        quality_level="mid",
        advanced_mode=False,
        rag_injection="",
    )
    system_instruction = _build_render_system_instruction(quality_level="mid")

    assert "Polio's grounded report render engine." in prompt
    assert "Environmental Engineering" in prompt
    assert "Quality University" in prompt
    assert "Maintain the provenance boundary at all times." in system_instruction
    assert "Return only valid JSON" in system_instruction


def test_render_quality_guardrail_uses_registry_assets() -> None:
    low = _build_quality_guardrail("low")
    high = _build_quality_guardrail("high")

    assert "[Render Quality Guardrail: Low]" in low
    assert "[Render Quality Guardrail: High]" in high


def _clear_quality_control_caches() -> None:
    quality_control._load_quality_profile_bundle.cache_clear()
    quality_control._load_workshop_choice_bundle.cache_clear()
    quality_control._get_quality_profiles.cache_clear()


def test_quality_control_runtime_uses_registry_assets(monkeypatch) -> None:
    fake_assets = {
        "system.guardrails.workshop-quality-profiles": {
            "profiles": {
                "low": {
                    "level": "low",
                    "label": "ì»¤ìŠ¤?€ ?ˆì „??,
                    "emoji": "L",
                    "color": "mint",
                    "description": "low description",
                    "detail": "low detail",
                    "student_fit": "low fit",
                    "safety_posture": "low posture",
                    "authenticity_policy": "low authenticity",
                    "hallucination_guardrail": "low guardrail",
                    "starter_mode": "low starter",
                    "followup_mode": "low followup",
                    "reference_policy": "optional",
                    "reference_intensity": "none",
                    "render_depth": "low depth",
                    "expression_policy": "low expression",
                    "advanced_features_allowed": False,
                    "max_output_chars": 100,
                    "temperature": 0.1,
                    "minimum_turn_count": 1,
                    "minimum_reference_count": 0,
                    "render_threshold": 10,
                },
                "mid": {
                    "level": "mid",
                    "label": "ì»¤ìŠ¤?€ ?œì???,
                    "emoji": "M",
                    "color": "blue",
                    "description": "mid description",
                    "detail": "mid detail",
                    "student_fit": "mid fit",
                    "safety_posture": "mid posture",
                    "authenticity_policy": "mid authenticity",
                    "hallucination_guardrail": "mid guardrail",
                    "starter_mode": "mid starter",
                    "followup_mode": "mid followup",
                    "reference_policy": "recommended",
                    "reference_intensity": "light",
                    "render_depth": "mid depth",
                    "expression_policy": "mid expression",
                    "advanced_features_allowed": False,
                    "max_output_chars": 200,
                    "temperature": 0.2,
                    "minimum_turn_count": 2,
                    "minimum_reference_count": 0,
                    "render_threshold": 20,
                },
                "high": {
                    "level": "high",
                    "label": "ì»¤ìŠ¤?€ ?¬í™”??,
                    "emoji": "H",
                    "color": "violet",
                    "description": "high description",
                    "detail": "high detail",
                    "student_fit": "high fit",
                    "safety_posture": "high posture",
                    "authenticity_policy": "high authenticity",
                    "hallucination_guardrail": "high guardrail",
                    "starter_mode": "high starter",
                    "followup_mode": "high followup",
                    "reference_policy": "required",
                    "reference_intensity": "required",
                    "render_depth": "high depth",
                    "expression_policy": "high expression",
                    "advanced_features_allowed": True,
                    "max_output_chars": 300,
                    "temperature": 0.3,
                    "minimum_turn_count": 3,
                    "minimum_reference_count": 1,
                    "render_threshold": 30,
                },
            }
        },
        "chat.workshop-choice-copy": {
            "starter_templates": {
                "low": [
                    {
                        "id": "custom_low_start",
                        "label": "ì»¤ìŠ¤?€ ?œì‘",
                        "description": "ì»¤ìŠ¤?€ ?¤ëª…",
                        "prompt_template": "{quest_label} / {major_label} / {output_label}",
                    }
                ],
                "mid": [
                    {
                        "id": "custom_mid_start",
                        "label": "ì¤‘ê°„ ?œì‘",
                        "description": "ì¤‘ê°„ ?¤ëª…",
                        "prompt_template": "{quest_label}",
                    }
                ],
                "high": [
                    {
                        "id": "custom_high_start",
                        "label": "?¬í™” ?œì‘",
                        "description": "?¬í™” ?¤ëª…",
                        "prompt_template": "{quest_label}",
                    }
                ],
            },
            "followup_templates": {
                "low": [
                    {
                        "id_template": "custom_low_followup_{turn_count}",
                        "label": "ì»¤ìŠ¤?€ ?„ì†",
                        "description": "?„ì† ?¤ëª…",
                        "prompt_template": "?„ì† ?„ë¡¬?„íŠ¸",
                    }
                ],
                "mid": [
                    {
                        "id_template": "custom_mid_followup_{turn_count}",
                        "label": "ì¤‘ê°„ ?„ì†",
                        "description": "ì¤‘ê°„ ?„ì† ?¤ëª…",
                        "prompt_template": "ì¤‘ê°„ ?„ì† ?„ë¡¬?„íŠ¸",
                    }
                ],
                "high": [
                    {
                        "id_template": "custom_high_followup_{turn_count}",
                        "label": "?¬í™” ?„ì†",
                        "description": "?¬í™” ?„ì† ?¤ëª…",
                        "prompt_template": "?¬í™” ?„ì† ?„ë¡¬?„íŠ¸",
                    }
                ],
            },
            "acknowledgements": {
                "choice_template": "[{profile_label}] {label} / {followup_mode}",
                "message_template": "[{profile_label}] {render_depth} / {guidance}",
                "guidance_template": "?¤ìŒ: {next_choice_label}",
            },
        },
    }

    class FakeRegistry:
        def get_asset(self, name: str) -> SimpleNamespace:
            return SimpleNamespace(body=json.dumps(fake_assets[name], ensure_ascii=False))

    monkeypatch.setattr(quality_control, "get_prompt_registry", lambda: FakeRegistry())
    _clear_quality_control_caches()

    try:
        profile = quality_control.get_quality_profile("low")
        starter_choices = quality_control.build_starter_choices(
            quality_level="low",
            quest_title="?êµ¬ ì£¼ì œ",
            target_major="êµìœ¡??,
            recommended_output_type="ë³´ê³ ??,
        )
        followup_choices = quality_control.build_followup_choices(
            quality_level="low",
            turn_count=7,
        )
        choice_ack = quality_control.build_choice_acknowledgement(
            quality_level="low",
            label="ì»¤ìŠ¤?€ ?œì‘",
        )
        message_ack = quality_control.build_message_acknowledgement(
            quality_level="low",
            next_choice_label="ì»¤ìŠ¤?€ ?„ì†",
        )
    finally:
        _clear_quality_control_caches()

    assert profile.label == "ì»¤ìŠ¤?€ ?ˆì „??
    assert starter_choices[0]["label"] == "ì»¤ìŠ¤?€ ?œì‘"
    assert starter_choices[0]["payload"]["prompt"] == "?êµ¬ ì£¼ì œ / êµìœ¡??/ ë³´ê³ ??
    assert followup_choices[0]["id"] == "custom_low_followup_7"
    assert choice_ack == "[ì»¤ìŠ¤?€ ?ˆì „?? ì»¤ìŠ¤?€ ?œì‘ / low followup"
    assert message_ack == "[ì»¤ìŠ¤?€ ?ˆì „?? low depth / ?¤ìŒ: ì»¤ìŠ¤?€ ?„ì†"

