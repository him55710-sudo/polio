from __future__ import annotations

from unifoli_api.services.diagnosis_scoring_service import build_diagnosis_scoring_sheet
from unifoli_api.services.student_record_feature_service import StudentRecordFeatures


def _sample_features() -> StudentRecordFeatures:
    return StudentRecordFeatures(
        source_mode="neis",
        document_count=1,
        total_word_count=1800,
        total_records=14,
        section_presence={
            "援먭낵?숈뒿諛쒕떖?곹솴": True,
            "李쎌쓽?곸껜?섑솢??: True,
            "?됰룞?뱀꽦 諛?醫낇빀?섍껄": True,
            "?낆꽌?쒕룞": False,
            "?섏긽寃쎈젰": True,
        },
        section_record_counts={
            "援먭낵?숈뒿諛쒕떖?곹솴": 7,
            "李쎌쓽?곸껜?섑솢??: 3,
            "?됰룞?뱀꽦 諛?醫낇빀?섍껄": 2,
            "?낆꽌?쒕룞": 0,
            "?섏긽寃쎈젰": 2,
        },
        subject_distribution={"?섑븰": 4, "臾쇰━": 3, "?뺣낫": 3},
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


def test_scoring_service_is_deterministic() -> None:
    features = _sample_features()

    first = build_diagnosis_scoring_sheet(
        features=features,
        project_title="determinism-check",
        target_major="而댄벂?곌났??,
        target_university="?뚯뒪?몃??숆탳",
    )
    second = build_diagnosis_scoring_sheet(
        features=features,
        project_title="determinism-check",
        target_major="而댄벂?곌났??,
        target_university="?뚯뒪?몃??숆탳",
    )

    assert first.model_dump() == second.model_dump()
    assert len(first.admission_axes) == 5
    assert {axis.key for axis in first.admission_axes} == {
        "major_alignment",
        "inquiry_continuity",
        "evidence_density",
        "process_explanation",
        "authenticity_risk",
    }
    assert all(0 <= axis.score <= 100 for axis in first.admission_axes)
    assert first.document_quality.parse_reliability_score >= 0


