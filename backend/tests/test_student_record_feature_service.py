from __future__ import annotations

from types import SimpleNamespace

from unifoli_api.services.student_record_feature_service import extract_student_record_features


def test_extract_student_record_features_tolerates_malformed_canonical_shapes() -> None:
    document = SimpleNamespace(
        content_text="?™ìƒ ê¸°ë¡ ?ìŠ¤??,
        content_markdown="",
        parse_metadata={
            "parse_confidence": 0.8,
            "analysis_artifact": {
                "canonical_data": {
                    "attendance": {"grade": 1},  # malformed: dict instead of list
                    "awards": "none",  # malformed: string instead of list
                    "grades": [{"subject": "?˜í•™"}, "bad-entry"],  # mixed list entries
                    "extracurricular_narratives": ["bad-list"],  # malformed: list instead of dict
                    "subject_special_notes": "bad-notes",  # malformed: string instead of dict
                    "reading_activities": {"title": "?…ì„œ"},  # malformed: dict instead of list
                    "behavior_opinion": {"text": "?±ì‹¤??},  # non-string value still acceptable
                },
                "quality_report": {"overall_score": "not-a-number"},
            }
        },
    )

    features = extract_student_record_features(
        documents=[document],
        full_text=document.content_text,
        target_major="ì»´í“¨?°ê³µ??,
        career_direction="AI",
    )

    assert features.document_count == 1
    assert features.total_word_count > 0
    assert features.section_presence["?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬"] is True
    assert features.section_record_counts["êµê³¼?™ìŠµë°œë‹¬?í™©"] >= 1
    assert features.subject_distribution.get("?˜í•™", 0) >= 1

