from __future__ import annotations

from unifoli_api.services.pdf_analysis_service import build_student_record_structure_metadata
from unifoli_ingest.models import ParsedChunkPayload, ParsedDocumentPayload


def test_build_student_record_structure_metadata_extracts_core_fields() -> None:
    parsed = ParsedDocumentPayload(
        parser_name="neis",
        source_extension=".pdf",
        page_count=3,
        word_count=300,
        content_text=(
            "2?™ë…„ 1?™ê¸° êµê³¼?™ìŠµë°œë‹¬?í™©?ì„œ ?°ì´??ë¶„ì„ ?êµ¬ë¥??˜í–‰?? "
            "?„ì† ?œë™?¼ë¡œ ë¹„êµ ?¤í—˜??ì§„í–‰?ˆê³  ê³¼ì •ê³??œê³„ë¥??±ì°°?? "
            "ì§„ë¡œ ?°ê³„ ë¬¸ì¥???µí•´ ?„ê³µ ?í•©?±ì„ ?¤ëª…??"
        ),
        content_markdown="",
        metadata={},
        chunks=[ParsedChunkPayload(
            chunk_index=0,
            page_number=1,
            char_start=0,
            char_end=120,
            token_estimate=40,
            content_text="?ŒìŠ¤??,
        )],
        raw_artifact={
            "pages": [
                {"page_number": 1, "text": "êµê³¼?™ìŠµë°œë‹¬?í™© ?¸ë??¥ë ¥ ?¹ê¸°?¬í•­"},
                {"page_number": 2, "text": "ì°½ì˜??ì²´í—˜?œë™ ?™ì•„ë¦?ì§„ë¡œ?œë™"},
                {"page_number": 3, "text": "?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬"},
            ]
        },
        masked_artifact={},
        analysis_artifact={},
        parse_confidence=0.8,
        needs_review=False,
    )

    structure = build_student_record_structure_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        analysis_artifact=None,
    )

    assert structure is not None
    assert "major_sections" in structure
    assert "section_density" in structure
    assert "timeline_signals" in structure
    assert "subject_major_alignment_signals" in structure
    assert "continuity_signals" in structure

