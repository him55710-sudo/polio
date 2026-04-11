from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from unifoli_api.schemas.diagnosis import DiagnosisResultPayload
from unifoli_api.services import diagnosis_report_service as report_service
from unifoli_api.services.prompt_registry import PromptAssetNotFoundError


def _build_minimal_result_payload() -> DiagnosisResultPayload:
    return DiagnosisResultPayload.model_validate(
        {
            "headline": "湲곗큹 吏꾨떒 ?ㅻ뱶?쇱씤",
            "strengths": ["?먭뎄 二쇱젣???쇨??깆씠 蹂댁엯?덈떎."],
            "gaps": ["洹쇨굅 臾몄옣怨??몄슜 ?곌껐????紐낇솗???댁빞 ?⑸땲??"],
            "recommended_focus": "洹쇨굅-二쇱옣 留ㅽ븨 媛뺥솕",
            "risk_level": "warning",
            "next_actions": ["?듭떖 二쇱옣 3媛쒖뿉 洹쇨굅 異쒖쿂瑜??곌껐?섏꽭??"],
            "recommended_topics": ["?꾧났 ?곌퀎 ?먭뎄 ?ы솕"],
            "citations": [
                {
                    "source_label": "?숈깮遺 湲곕줉",
                    "page_number": 2,
                    "excerpt": "?먭뎄 ?쒕룞??怨쇱젙怨?寃곌낵媛 ?뺣━??,
                    "relevance_score": 1.7,
                }
            ],
        }
    )


def test_build_consultant_report_payload_contains_expected_sections(monkeypatch) -> None:
    async def fake_narratives(**kwargs):  # noqa: ANN003
        return report_service._ConsultantNarrativePayload(
            executive_summary="?붿빟 臾몄옣",
            final_consultant_memo="理쒖쥌 硫붾え 臾몄옣",
        )

    monkeypatch.setattr(report_service, "_generate_narratives", fake_narratives)

    run = SimpleNamespace(id="run-1")
    project = SimpleNamespace(
        id="project-1",
        title="?뚯뒪???꾨줈?앺듃",
        target_university="?쒖슱??숆탳",
        target_major="而댄벂?곌났??,
    )
    result = _build_minimal_result_payload()
    documents = [
        SimpleNamespace(
            parse_metadata={
                "student_record_structure": {
                    "section_density": {"?명듅": 0.8, "李쎌껜": 0.4},
                    "weak_sections": ["吏꾨줈"],
                    "timeline_signals": ["2?숇뀈", "3?숇뀈"],
                    "activity_clusters": ["?먭뎄/?ㅽ뿕"],
                    "subject_major_alignment_signals": ["?꾧났 ?곌퀎 臾몄옣 ?뺤씤"],
                    "continuity_signals": ["?꾩냽 ?먭뎄 怨꾪쉷"],
                    "process_reflection_signals": ["?쒓퀎? 媛쒖꽑??],
                    "uncertain_items": [],
                }
            }
        )
    ]

    report = asyncio.run(
        report_service.build_consultant_report_payload(
            run=run,
            project=project,
            result=result,
            report_mode="premium_10p",
            template_id="consultant_diagnosis_premium_10p",
            include_appendix=True,
            include_citations=True,
            documents=documents,
        )
    )

    section_ids = {section.id for section in report.sections}
    assert "executive_summary" in section_ids
    assert "record_baseline_dashboard" in section_ids
    assert "interview_questions" in section_ids
    assert "roadmap" in section_ids
    assert report.render_hints["minimum_pages"] == 10
    assert report.render_hints["section_order"] == list(report_service._PREMIUM_SECTION_ORDER)
    assert report.score_groups
    assert {group.group for group in report.score_groups} == {"student_evaluation", "system_quality"}
    design_contract = report.render_hints.get("design_contract")
    assert isinstance(design_contract, dict)
    assert design_contract.get("contract_id") == "diagnosis_report_premium_v2"
    section_hierarchy = design_contract.get("section_hierarchy")
    assert isinstance(section_hierarchy, dict)
    required_order = section_hierarchy.get("required_order")
    assert isinstance(required_order, list)
    assert required_order[0] == "executive_summary"
    assert required_order[-1] == "roadmap"
    assert len(report.roadmap) == 3
    assert report.citations == []


def test_generate_consultant_report_artifact_requires_completed_diagnosis(monkeypatch) -> None:
    monkeypatch.setattr(report_service, "get_latest_report_artifact_for_run", lambda *args, **kwargs: None)

    run = SimpleNamespace(id="run-2", result_payload=None)
    project = SimpleNamespace(
        id="project-2",
        title="吏꾨떒 誘몄셿猷??꾨줈?앺듃",
        target_university=None,
        target_major=None,
    )

    with pytest.raises(ValueError, match="Diagnosis is not complete yet"):
        asyncio.run(
            report_service.generate_consultant_report_artifact(
                SimpleNamespace(),
                run=run,
                project=project,
                report_mode="compact",
                template_id=None,
                include_appendix=True,
                include_citations=True,
                force_regenerate=False,
            )
        )


def test_generate_consultant_report_artifact_fallbacks_to_failed_status(monkeypatch) -> None:
    class FakeDB:
        def __init__(self) -> None:
            self.added = []

        def add(self, obj) -> None:  # noqa: ANN001
            self.added.append(obj)

        def commit(self) -> None:
            return None

        def refresh(self, obj) -> None:  # noqa: ANN001
            return None

    async def failing_payload_builder(**kwargs):  # noqa: ANN003
        raise RuntimeError("payload generation failure")

    monkeypatch.setattr(report_service, "get_latest_report_artifact_for_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(report_service, "build_consultant_report_payload", failing_payload_builder)
    monkeypatch.setattr(report_service, "list_documents_for_project", lambda *args, **kwargs: [])

    db = FakeDB()
    run = SimpleNamespace(
        id="run-3",
        result_payload=_build_minimal_result_payload().model_dump_json(),
    )
    project = SimpleNamespace(
        id="project-3",
        title="?ㅽ뙣 ?대갚 ?꾨줈?앺듃",
        target_university="?곗꽭??숆탳",
        target_major="?꾧린?꾩옄怨듯븰",
    )

    artifact = asyncio.run(
        report_service.generate_consultant_report_artifact(
            db,
            run=run,
            project=project,
            report_mode="compact",
            template_id=None,
            include_appendix=True,
            include_citations=True,
            force_regenerate=False,
        )
    )

    assert artifact.status == "FAILED"
    assert artifact.error_message
    assert db.added


def test_generate_narratives_uses_deterministic_fallback_when_prompt_registry_missing(monkeypatch) -> None:
    class _BrokenRegistry:
        def compose_prompt(self, name: str) -> str:
            raise PromptAssetNotFoundError(f"missing prompt: {name}")

    def _unexpected_llm_client(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("LLM client should not be requested when prompt registry is unavailable")

    monkeypatch.setattr(report_service, "get_prompt_registry", lambda: _BrokenRegistry())
    monkeypatch.setattr(report_service, "get_llm_client", _unexpected_llm_client)

    payload = asyncio.run(
        report_service._generate_narratives(  # noqa: SLF001
            project=SimpleNamespace(
                id="project-registry-missing",
                title="Prompt Registry Missing Project",
                target_university="?곗꽭??숆탳",
                target_major="寃쎌쁺?숆낵",
            ),
            result=_build_minimal_result_payload(),
            document_structure={"weak_sections": ["吏꾨줈"], "section_density": {"?명듅": 0.5}},
            uncertainty_notes=["?숈깮遺 ?쇰? ?섏씠吏???먮룆 ?좊ː?꾧? ??뒿?덈떎."],
        )
    )

    assert payload.execution_metadata["fallback_used"] is True
    assert payload.execution_metadata["fallback_reason"] == "prompt_registry_unavailable"
    assert payload.narrative.executive_summary
    assert payload.narrative.final_consultant_memo


def _evidence_bank_sample(count: int = 12) -> list[dict[str, object]]:
    bank: list[dict[str, object]] = []
    for index in range(count):
        page = (index % 6) + 1
        bank.append(
            {
                "anchor_id": f"ev-{index}",
                "page": page,
                "section": "李쎌쓽??泥댄뿕?쒕룞",
                "normalized_section": "creative_activities",
                "quote": f"吏?띻???嫄댁텞 ?먭뎄 洹쇨굅 臾몄옣 {index}",
                "major_relevance": ["嫄댁텞", "?섍꼍"],
                "process_elements": {
                    "motivation": True,
                    "method": True,
                    "finding": True,
                    "limitation": index % 2 == 0,
                    "extension": True,
                },
                "confidence": 0.9,
            }
        )
    return bank


def test_score_groups_keep_student_and_system_scores_separate(monkeypatch) -> None:
    async def fake_narratives(**kwargs):  # noqa: ANN003
        return report_service._ConsultantNarrativePayload(
            executive_summary="?붿빟",
            final_consultant_memo="硫붾え",
        )

    monkeypatch.setattr(report_service, "_generate_narratives", fake_narratives)

    run = SimpleNamespace(id="run-score-groups")
    project = SimpleNamespace(id="project-score-groups", title="?뚯뒪??, target_university="?쒖슱??숆탳", target_major="嫄댁텞?숆낵")
    result = _build_minimal_result_payload()
    documents = [
        SimpleNamespace(
            parse_metadata={
                "student_record_canonical": {
                    "evidence_bank": _evidence_bank_sample(),
                    "quality_gates": {"reanalysis_required": False, "missing_required_sections": []},
                    "section_coverage": {
                        "section_counts": {"grades_subjects": 2},
                        "coverage_score": 1.0,
                        "missing_sections": [],
                        "reanalysis_required": False,
                    },
                    "section_classification": {
                        "grades_subjects": {"density": 0.9},
                        "subject_special_notes": {"density": 0.9},
                        "extracurricular": {"density": 0.8},
                        "career_signals": {"density": 0.8},
                        "reading_activity": {"density": 0.7},
                        "behavior_opinion": {"density": 0.7},
                    },
                },
                "student_record_structure": {
                    "section_density": {"援먭낵?숈뒿諛쒕떖?곹솴": 0.9, "李쎌껜": 0.8, "?됰룞?뱀꽦": 0.7},
                    "coverage_check": {"coverage_score": 1.0, "reanalysis_required": False, "missing_required_sections": []},
                    "contradiction_check": {"passed": True, "items": []},
                },
            }
        )
    ]

    report = asyncio.run(
        report_service.build_consultant_report_payload(
            run=run,
            project=project,
            result=result,
            report_mode="premium_10p",
            template_id="consultant_diagnosis_premium_10p",
            include_appendix=True,
            include_citations=True,
            documents=documents,
        )
    )

    assert report.score_groups
    student_group = next(group for group in report.score_groups if group.group == "student_evaluation")
    system_group = next(group for group in report.score_groups if group.group == "system_quality")
    assert {block.key for block in student_group.blocks} >= {
        "major_fit",
        "inquiry_depth",
        "inquiry_continuity",
        "evidence_density",
        "process_explanation",
        "design_spatial_thinking",
        "academic_base",
        "leadership_collaboration",
    }
    assert {block.key for block in system_group.blocks} == {
        "parse_coverage",
        "citation_coverage",
        "evidence_uniqueness",
        "contradiction_check",
        "redaction_safety",
    }


def test_contradiction_check_blocks_premium_render(monkeypatch) -> None:
    async def fake_narratives(**kwargs):  # noqa: ANN003
        return report_service._ConsultantNarrativePayload(
            executive_summary="?붿빟",
            final_consultant_memo="硫붾え",
        )

    monkeypatch.setattr(report_service, "_generate_narratives", fake_narratives)

    run = SimpleNamespace(id="run-contradiction")
    project = SimpleNamespace(id="project-contradiction", title="?뚯뒪??, target_university="?쒖슱??숆탳", target_major="嫄댁텞?숆낵")
    result = _build_minimal_result_payload()
    documents = [
        SimpleNamespace(
            parse_metadata={
                "student_record_structure": {
                    "section_density": {"援먭낵?숈뒿諛쒕떖?곹솴": 1.0},
                    "weak_sections": ["援먭낵?숈뒿諛쒕떖?곹솴"],
                    "coverage_check": {"coverage_score": 1.0, "reanalysis_required": False, "missing_required_sections": []},
                    "contradiction_check": {
                        "passed": False,
                        "items": [{"section": "援먭낵?숈뒿諛쒕떖?곹솴", "reason": "weak_or_missing_conflicts_with_density"}],
                    },
                }
            }
        )
    ]

    with pytest.raises(ValueError, match="contradiction_check_failed"):
        asyncio.run(
            report_service.build_consultant_report_payload(
                run=run,
                project=project,
                result=result,
                report_mode="premium_10p",
                template_id="consultant_diagnosis_premium_10p",
                include_appendix=True,
                include_citations=True,
                documents=documents,
            )
        )


def test_premium_report_sections_keep_diverse_evidence_anchors(monkeypatch) -> None:
    async def fake_narratives(**kwargs):  # noqa: ANN003
        return report_service._ConsultantNarrativePayload(
            executive_summary="?붿빟",
            final_consultant_memo="硫붾え",
        )

    monkeypatch.setattr(report_service, "_generate_narratives", fake_narratives)

    run = SimpleNamespace(id="run-diverse-anchors")
    project = SimpleNamespace(id="project-diverse-anchors", title="?뚯뒪??, target_university="?쒖슱??숆탳", target_major="嫄댁텞?숆낵")
    result = _build_minimal_result_payload()
    documents = [
        SimpleNamespace(
            parse_metadata={
                "student_record_canonical": {
                    "evidence_bank": _evidence_bank_sample(count=24),
                    "quality_gates": {"reanalysis_required": False, "missing_required_sections": []},
                    "section_coverage": {
                        "section_counts": {"grades_subjects": 6, "subject_special_notes": 6, "creative_activities": 6},
                        "coverage_score": 1.0,
                        "missing_sections": [],
                        "reanalysis_required": False,
                    },
                    "section_classification": {
                        "grades_subjects": {"density": 0.95},
                        "subject_special_notes": {"density": 0.95},
                        "creative_activities": {"density": 0.9},
                        "behavior_general_comments": {"density": 0.8},
                    },
                },
                "student_record_structure": {
                    "section_density": {"援먭낵?숈뒿諛쒕떖?곹솴": 0.95, "?명듅": 0.95, "李쎌껜": 0.9, "?됰룞?뱀꽦": 0.8},
                    "coverage_check": {"coverage_score": 1.0, "reanalysis_required": False, "missing_required_sections": []},
                    "contradiction_check": {"passed": True, "items": []},
                },
            }
        )
    ]

    report = asyncio.run(
        report_service.build_consultant_report_payload(
            run=run,
            project=project,
            result=result,
            report_mode="premium_10p",
            template_id="consultant_diagnosis_premium_10p",
            include_appendix=True,
            include_citations=True,
            documents=documents,
        )
    )

    all_evidence = [item for section in report.sections for item in section.evidence_items]
    unique_anchor_labels = {item.source_label for item in all_evidence if item.source_label}
    unique_pages = {int(item.page_number) for item in all_evidence if isinstance(item.page_number, int) and item.page_number > 0}

    assert len(unique_anchor_labels) >= 10
    assert len(unique_pages) >= 6


