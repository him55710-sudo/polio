from __future__ import annotations

from unifoli_api.services.admissions_criteria_service import validate_admissions_criteria_corpus
from unifoli_api.services.diagnosis_scoring_service import (
    AxisSemanticGrade,
    SemanticDiagnosisExtraction,
    build_diagnosis_scoring_sheet,
)
from unifoli_api.services.student_record_feature_service import StudentRecordFeatures


def _sample_features() -> StudentRecordFeatures:
    return StudentRecordFeatures(
        source_mode="structured",
        document_count=1,
        total_word_count=1800,
        total_records=14,
        section_presence={
            "교과학습발달상황": True,
            "창의적 체험활동": True,
            "행동특성 및 종합의견": True,
            "독서활동": False,
            "수상경력": True,
        },
        section_record_counts={
            "교과학습발달상황": 7,
            "창의적 체험활동": 3,
            "행동특성 및 종합의견": 2,
            "독서활동": 0,
            "수상경력": 2,
        },
        subject_distribution={"수학": 4, "물리": 3, "정보": 3},
        unique_subject_count=3,
        narrative_char_count=4200,
        narrative_density=0.58,
        evidence_reference_count=11,
        evidence_density=0.72,
        repeated_subject_ratio=0.55,
        major_term_overlap_ratio=0.62,
        avg_parse_confidence=0.81,
        reliability_score=0.79,
        needs_review=False,
        needs_review_documents=0,
        risk_flags=[],
    )


def _thin_features() -> StudentRecordFeatures:
    return StudentRecordFeatures(
        source_mode="text",
        document_count=1,
        total_word_count=600,
        total_records=4,
        section_presence={
            "교과학습발달상황": True,
            "창의적 체험활동": True,
            "행동특성 및 종합의견": False,
            "독서활동": False,
            "수상경력": False,
        },
        section_record_counts={
            "교과학습발달상황": 2,
            "창의적 체험활동": 1,
            "행동특성 및 종합의견": 0,
            "독서활동": 0,
            "수상경력": 0,
        },
        subject_distribution={"수학": 1, "과학": 1},
        unique_subject_count=2,
        narrative_char_count=900,
        narrative_density=0.25,
        evidence_reference_count=2,
        evidence_density=0.18,
        repeated_subject_ratio=0.1,
        major_term_overlap_ratio=0.08,
        avg_parse_confidence=0.52,
        reliability_score=0.52,
        needs_review=False,
        needs_review_documents=0,
        risk_flags=[],
    )


def _high_semantic() -> SemanticDiagnosisExtraction:
    grade = AxisSemanticGrade(score=95, rationale="강한 의미론 점수", evidence_hints=["강점 단서"])
    return SemanticDiagnosisExtraction(
        universal_rigor=grade,
        universal_specificity=grade,
        relational_narrative=grade,
        relational_continuity=grade,
        cluster_depth=grade,
        cluster_suitability=grade,
        community_contribution=grade,
        summary_insight="강하게 평가됨",
    )


def test_admissions_criteria_corpus_is_source_backed() -> None:
    assert validate_admissions_criteria_corpus() == []


def test_scoring_service_is_deterministic_and_uses_eight_axes() -> None:
    features = _sample_features()

    first = build_diagnosis_scoring_sheet(
        features=features,
        project_title="determinism-check",
        target_major="컴퓨터공학",
        target_university="연세대학교",
    )
    second = build_diagnosis_scoring_sheet(
        features=features,
        project_title="determinism-check",
        target_major="컴퓨터공학",
        target_university="연세대학교",
    )

    assert first.model_dump() == second.model_dump()
    assert len(first.admission_axes) == 8
    assert {axis.key for axis in first.admission_axes} == {
        "universal_rigor",
        "universal_specificity",
        "relational_narrative",
        "relational_continuity",
        "cluster_depth",
        "cluster_suitability",
        "community_contribution",
        "authenticity_risk",
    }
    assert all(0 <= axis.score <= 100 for axis in first.admission_axes)
    assert all(axis.criteria_refs for axis in first.admission_axes)
    assert all(axis.input_factors for axis in first.admission_axes)
    assert all(axis.confidence_note for axis in first.admission_axes)
    assert first.document_quality.parse_reliability_score >= 0


def test_calibration_is_warmer_but_keeps_thin_records_below_strong_band() -> None:
    solid = build_diagnosis_scoring_sheet(
        features=_sample_features(),
        project_title="calibration-check",
        target_major="컴퓨터공학",
        target_university="연세대학교",
    )
    solid_scores = {axis.key: axis.score for axis in solid.admission_axes}

    assert solid_scores["universal_rigor"] >= 78
    assert solid_scores["universal_specificity"] >= 78

    thin = build_diagnosis_scoring_sheet(
        features=_thin_features(),
        project_title="thin-record-check",
        target_major="컴퓨터공학",
        target_university="연세대학교",
        semantic=_high_semantic(),
    )
    thin_positive_scores = [axis.score for axis in thin.admission_axes if axis.key != "authenticity_risk"]

    assert max(thin_positive_scores) < 80


def test_community_axis_uses_behavior_records_and_policy_risk() -> None:
    solid = build_diagnosis_scoring_sheet(
        features=_sample_features(),
        project_title="community-check",
        target_major="사회학",
        target_university="서울시립대학교",
    )
    solid_scores = {axis.key: axis.score for axis in solid.admission_axes}

    assert solid_scores["community_contribution"] >= 70
    community_axis = next(axis for axis in solid.admission_axes if axis.key == "community_contribution")
    assert any("common_elements_2022" in ref or "kcue_2026_basic" in ref for ref in community_axis.criteria_refs)

    risky = _sample_features().model_copy(
        update={
            "risk_flags": ["학교폭력"],
            "needs_review": True,
            "needs_review_documents": 1,
        }
    )
    risky_sheet = build_diagnosis_scoring_sheet(
        features=risky,
        project_title="community-risk-check",
        target_major="사회학",
        target_university="서울시립대학교",
    )
    risky_scores = {axis.key: axis.score for axis in risky_sheet.admission_axes}

    assert risky_scores["authenticity_risk"] > solid_scores["authenticity_risk"]
    assert risky_scores["community_contribution"] < solid_scores["community_contribution"]
