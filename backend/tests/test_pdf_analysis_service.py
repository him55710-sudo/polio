from __future__ import annotations

from unifoli_api.core.config import Settings
from unifoli_api.core.llm import OllamaClient, get_pdf_analysis_llm_client
from unifoli_api.services.pdf_analysis_service import (
    build_pdf_analysis_metadata,
    build_student_record_canonical_metadata,
    build_student_record_structure_metadata,
)
from unifoli_ingest.models import ParsedChunkPayload, ParsedDocumentPayload


class _FakePdfLLM:
    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        return response_model(
            summary="ë¬¸ì„œ???µì‹¬ ?ë¦„???˜ì´ì§€ë³„ë¡œ ë¹„êµ??ëª…í™•?˜ê²Œ ?•ì¸?©ë‹ˆ??",
            key_points=["?œë™ ?™ê¸°", "ê³¼ì • ê¸°ë¡", "ê²°ê³¼?€ ?±ì°°"],
            page_insights=[
                {"page_number": 1, "summary": "1?˜ì´ì§€?ëŠ” ?œë™ ë°°ê²½ê³?ëª©í‘œê°€ ?•ë¦¬?˜ì–´ ?ˆìŠµ?ˆë‹¤."},
                {"page_number": 2, "summary": "2?˜ì´ì§€?ëŠ” ?˜í–‰ ê³¼ì •ê³?ê²°ê³¼ê°€ ?´ì–´ì§‘ë‹ˆ??"},
            ],
            evidence_gaps=["?¼ë? ?˜ì¹˜ ê·¼ê±°???ë¬¸ ?¬í™•?¸ì´ ?„ìš”?©ë‹ˆ??"],
        )


class _TextFallbackPdfLLM:
    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        raise RuntimeError("json schema response unsupported")

    async def stream_chat(self, prompt, system_instruction=None, temperature=0.5):  # noqa: ANN001
        yield (
            "## PDF ?˜ì´ì§€ë³??µì‹¬ ?”ì•½\n"
            "?„ì²´ ?”ì•½: ë¬¸ì„œ ?ë¦„???˜ì´ì§€ë³„ë¡œ ê²€? í–ˆ?µë‹ˆ??\n"
            "1?˜ì´ì§€: ?œë™ ë°°ê²½ê³?ëª©í‘œê°€ ?•ë¦¬?˜ì–´ ?ˆìŠµ?ˆë‹¤.\n"
            "2?˜ì´ì§€: ?˜í–‰ ê³¼ì •ê³?ê²°ê³¼ê°€ ?´ì–´ì§‘ë‹ˆ??\n"
            "ê·¼ê±° ë¶€ì¡? ?¼ë? ?˜ì¹˜???ë¬¸ ?¬í™•?¸ì´ ?„ìš”?©ë‹ˆ??\n"
        )


class _FailingPdfLLM:
    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        raise RuntimeError("forced llm failure")

    async def stream_chat(self, prompt, system_instruction=None, temperature=0.5):  # noqa: ANN001
        if False:
            yield ""
        raise RuntimeError("forced stream failure")


def _build_sample_payload() -> ParsedDocumentPayload:
    return ParsedDocumentPayload(
        parser_name="pymupdf",
        source_extension=".pdf",
        page_count=2,
        word_count=120,
        content_text="1?˜ì´ì§€ ?œë™ ë°°ê²½ê³?ëª©í‘œ. 2?˜ì´ì§€ ?˜í–‰ ê³¼ì •ê³?ê²°ê³¼.",
        content_markdown="## Page 1\n?œë™ ë°°ê²½ê³?ëª©í‘œ\n\n## Page 2\n?˜í–‰ ê³¼ì •ê³?ê²°ê³¼",
        metadata={},
        chunks=[
            ParsedChunkPayload(
                chunk_index=0,
                page_number=1,
                char_start=0,
                char_end=30,
                token_estimate=8,
                content_text="?œë™ ë°°ê²½ê³?ëª©í‘œ",
            )
        ],
        masked_artifact={
            "pages": [
                {"page_number": 1, "masked_text": "?œë™ ë°°ê²½ê³?ëª©í‘œê°€ ?ì„¸??ê¸°ë¡?˜ì–´ ?ˆìŠµ?ˆë‹¤."},
                {"page_number": 2, "masked_text": "?˜í–‰ ê³¼ì •ê³?ê²°ê³¼, ?¤ìŒ ê³„íš???¬í•¨?˜ì–´ ?ˆìŠµ?ˆë‹¤."},
            ]
        },
    )


def _build_student_record_payload(*, parse_confidence: float = 0.82, needs_review: bool = False) -> ParsedDocumentPayload:
    return ParsedDocumentPayload(
        parser_name="neis",
        source_extension=".pdf",
        page_count=3,
        word_count=540,
        content_text=(
            "2?™ë…„ 1?™ê¸° êµê³¼?™ìŠµë°œë‹¬?í™© ?˜í•™ ê³¼ëª©?ì„œ ?êµ¬ ?„ë¡œ?íŠ¸ë¥??˜í–‰?? "
            "?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­??ë¬¸ì œ ?´ê²° ê³¼ì •ê³??¼ë“œë°±ì´ ê¸°ë¡?? "
            "ì°½ì˜??ì²´í—˜?œë™ ?™ì•„ë¦¬ì? ë´‰ì‚¬?œë™, ì§„ë¡œ?œë™???´ì–´ì¡Œê³  ì§„ë¡œ ?¬ë§ ?™ê³¼?€ ?°ê³„?? "
            "?…ì„œ ?œë™ê³??‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬???¬í•¨??"
        ),
        content_markdown="",
        metadata={},
        chunks=[
            ParsedChunkPayload(
                chunk_index=0,
                page_number=1,
                char_start=0,
                char_end=220,
                token_estimate=80,
                content_text="êµê³¼?™ìŠµë°œë‹¬?í™© ?˜í•™ ê³¼ëª© ?êµ¬ ?„ë¡œ?íŠ¸",
            )
        ],
        raw_artifact={
            "pages": [
                {
                    "page_number": 1,
                    "text": "2?™ë…„ 1?™ê¸° êµê³¼?™ìŠµë°œë‹¬?í™© ?˜í•™ ê³¼ëª© ?êµ¬ ?„ë¡œ?íŠ¸ ?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­",
                },
                {
                    "page_number": 2,
                    "text": "ì°½ì˜??ì²´í—˜?œë™ ?™ì•„ë¦?ë´‰ì‚¬?œë™ ì§„ë¡œ?œë™ ?¬ë§ ?™ê³¼ ?°ê³„",
                },
                {
                    "page_number": 3,
                    "text": "?…ì„œ ?œë™ ?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬",
                },
            ]
        },
        masked_artifact={
            "pages": [
                {
                    "page_number": 1,
                    "masked_text": "2?™ë…„ 1?™ê¸° êµê³¼?™ìŠµë°œë‹¬?í™© ?˜í•™ ê³¼ëª© ?êµ¬ ?„ë¡œ?íŠ¸ ?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­",
                },
                {
                    "page_number": 2,
                    "masked_text": "ì°½ì˜??ì²´í—˜?œë™ ?™ì•„ë¦?ë´‰ì‚¬?œë™ ì§„ë¡œ?œë™ ?¬ë§ ?™ê³¼ ?°ê³„",
                },
                {
                    "page_number": 3,
                    "masked_text": "?…ì„œ ?œë™ ?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬",
                },
            ]
        },
        parse_confidence=parse_confidence,
        needs_review=needs_review,
    )


def test_pdf_analysis_uses_dedicated_model(monkeypatch) -> None:
    settings = Settings(
        pdf_analysis_llm_enabled=True,
        pdf_analysis_llm_provider="ollama",
        pdf_analysis_ollama_model="gemma4-pdf",
        pdf_analysis_ollama_base_url="http://localhost:11434/v1",
    )
    monkeypatch.setattr("unifoli_api.services.pdf_analysis_service.get_settings", lambda: settings)
    monkeypatch.setattr("unifoli_api.services.pdf_analysis_service.get_pdf_analysis_llm_client", lambda: _FakePdfLLM())

    metadata = build_pdf_analysis_metadata(_build_sample_payload())

    assert metadata is not None
    assert metadata["engine"] == "llm"
    assert metadata["model"] == "gemma4-pdf"
    assert metadata["requested_pdf_analysis_provider"] == "ollama"
    assert metadata["actual_pdf_analysis_provider"] == "ollama"
    assert metadata["fallback_used"] is False
    assert isinstance(metadata["processing_duration_ms"], int)
    assert metadata["summary"]
    assert len(metadata["page_insights"]) >= 1


def test_pdf_analysis_falls_back_without_crashing(monkeypatch) -> None:
    settings = Settings(
        pdf_analysis_llm_enabled=True,
        pdf_analysis_llm_provider="ollama",
        pdf_analysis_ollama_model="gemma4-pdf",
    )
    monkeypatch.setattr("unifoli_api.services.pdf_analysis_service.get_settings", lambda: settings)
    monkeypatch.setattr("unifoli_api.services.pdf_analysis_service.get_pdf_analysis_llm_client", lambda: _FailingPdfLLM())

    metadata = build_pdf_analysis_metadata(_build_sample_payload())

    assert metadata is not None
    assert metadata["engine"] == "fallback"
    assert metadata["attempted_provider"] == "ollama"
    assert metadata["attempted_model"] == "gemma4-pdf"
    assert metadata["actual_pdf_analysis_provider"] == "heuristic"
    assert metadata["fallback_used"] is True
    assert metadata["failure_reason"]
    assert metadata["summary"]
    assert len(metadata["page_insights"]) >= 1


def test_pdf_analysis_recovers_from_text_only_llm(monkeypatch) -> None:
    settings = Settings(
        pdf_analysis_llm_enabled=True,
        pdf_analysis_llm_provider="ollama",
        pdf_analysis_ollama_model="gemma4-pdf",
    )
    monkeypatch.setattr("unifoli_api.services.pdf_analysis_service.get_settings", lambda: settings)
    monkeypatch.setattr("unifoli_api.services.pdf_analysis_service.get_pdf_analysis_llm_client", lambda: _TextFallbackPdfLLM())

    metadata = build_pdf_analysis_metadata(_build_sample_payload())

    assert metadata is not None
    assert metadata["engine"] == "llm"
    assert metadata["attempted_provider"] == "ollama"
    assert metadata["attempted_model"] == "gemma4-pdf"
    assert metadata["recovered_from_text_fallback"] is True
    assert metadata["fallback_used"] is True
    assert metadata["fallback_reason"] == "recovered_from_text_fallback"
    assert metadata["summary"]
    assert len(metadata["page_insights"]) >= 1
    assert metadata["page_insights"][0]["page_number"] == 1


def test_get_pdf_analysis_llm_client_uses_split_config(monkeypatch) -> None:
    settings = Settings(
        pdf_analysis_llm_enabled=True,
        pdf_analysis_llm_provider="ollama",
        pdf_analysis_ollama_model="gemma4-pdf",
        pdf_analysis_ollama_base_url="http://localhost:11434/v1",
        pdf_analysis_timeout_seconds=33,
        pdf_analysis_keep_alive="10m",
        pdf_analysis_num_ctx=1111,
        pdf_analysis_num_predict=222,
        pdf_analysis_num_thread=3,
    )
    monkeypatch.setattr("unifoli_api.core.llm.get_settings", lambda: settings)

    client = get_pdf_analysis_llm_client()

    assert isinstance(client, OllamaClient)
    assert client.model == "gemma4-pdf"
    assert client.options["num_ctx"] == 1111
    assert client.options["num_predict"] == 222
    assert client.options["num_thread"] == 3


def test_student_record_canonical_metadata_contains_required_fields_and_evidence() -> None:
    parsed = _build_student_record_payload()
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        analysis_artifact=None,
    )

    assert canonical is not None
    for key in (
        "record_type",
        "document_confidence",
        "timeline_signals",
        "grades_subjects",
        "subject_special_notes",
        "extracurricular",
        "career_signals",
        "reading_activity",
        "behavior_opinion",
        "major_alignment_hints",
        "weak_or_missing_sections",
        "uncertainties",
    ):
        assert key in canonical

    assert canonical["record_type"] == "korean_student_record_pdf"
    assert canonical["pipeline_stages"]
    assert canonical["document_confidence"] > 0.1
    assert canonical["timeline_signals"]
    assert canonical["grades_subjects"]
    first_subject = canonical["grades_subjects"][0]
    assert isinstance(first_subject.get("evidence"), list)
    assert first_subject["evidence"]
    assert first_subject["evidence"][0]["page_number"] >= 1


def test_student_record_canonical_metadata_marks_uncertainty_without_guessing() -> None:
    parsed = _build_student_record_payload(parse_confidence=0.32, needs_review=True)
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "fallback", "summary": "?´ë¦¬?¤í‹±"},
        analysis_artifact=None,
    )

    assert canonical is not None
    assert canonical["document_confidence"] < 0.8
    assert canonical["uncertainties"]
    uncertainty_messages = [str(item.get("message") or "") for item in canonical["uncertainties"]]
    assert any("confidence" in message or "ê²€?? in message for message in uncertainty_messages)


def test_student_record_structure_bridge_uses_canonical_schema() -> None:
    parsed = _build_student_record_payload()
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        analysis_artifact=None,
    )
    structure = build_student_record_structure_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        canonical_schema=canonical,
    )

    assert structure is not None
    assert structure["section_density"]["êµê³¼?™ìŠµë°œë‹¬?í™©"] > 0
    assert structure["timeline_signals"]
    assert "subject_major_alignment_signals" in structure


def _build_full_section_payload() -> ParsedDocumentPayload:
    pages = [
        {"page_number": 1, "text": "?¸ì ?¬í•­ ?±ëª… ?ê¸¸???™êµëª??ŒìŠ¤?¸ê³ ?±í•™êµ?},
        {"page_number": 2, "text": "ì¶œê²°?í™© ê²°ì„ ì§€ê°?ì¡°í‡´ ?†ìŒ"},
        {"page_number": 3, "text": "?˜ìƒê²½ë ¥ ?˜ìƒëª?ê³¼í•™?êµ¬ë°œí‘œ?€???˜ì—¬ê¸°ê? êµë‚´"},
        {"page_number": 4, "text": "ì°½ì˜??ì²´í—˜?œë™ ?™ì•„ë¦¬í™œ??ì§„ë¡œ?œë™ ì§€?ê???ê±´ì¶• ?êµ¬"},
        {"page_number": 5, "text": "ë´‰ì‚¬?œë™ ì§€??‚¬???˜ê²½?•í™” ë´‰ì‚¬?œê°„ 20?œê°„"},
        {"page_number": 6, "text": "êµê³¼?™ìŠµë°œë‹¬?í™© ê³¼ëª© ?˜í•™ ë¬¼ë¦¬ ?±ì·¨???°ìˆ˜"},
        {"page_number": 7, "text": "?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­ ê±´ì¶• ?¬ë£Œ êµ¬ì¡° ë¶„ì„ ?„ë¡œ?íŠ¸ ?˜í–‰"},
        {"page_number": 8, "text": "?…ì„œ?œë™?í™© ?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬ ?¬ìš©??ê²½í—˜ ê³µê°„ ?¸ë¬¸ ë³´ì™„"},
        {"page_number": 9, "text": "êµê³¼?™ìŠµë°œë‹¬?í™© ê³¼ëª© ?ì–´ ê³¼í•™ ?±ì·¨???°ìˆ˜"},
        {"page_number": 10, "text": "?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­ ê¸°í›„ ?€??ê±´ì¶• ?¤ê³„ ?•ì¥ ?œë™"},
    ]
    return ParsedDocumentPayload(
        parser_name="neis",
        source_extension=".pdf",
        page_count=len(pages),
        word_count=1500,
        content_text=" ".join(page["text"] for page in pages),
        content_markdown="",
        metadata={},
        chunks=[
            ParsedChunkPayload(
                chunk_index=0,
                page_number=1,
                char_start=0,
                char_end=120,
                token_estimate=40,
                content_text=pages[0]["text"],
            )
        ],
        raw_artifact={"pages": pages},
        masked_artifact={"pages": [{"page_number": page["page_number"], "masked_text": page["text"]} for page in pages]},
        parse_confidence=0.88,
        needs_review=False,
    )


def _build_normalized_artifact_only_payload() -> ParsedDocumentPayload:
    page_texts = [
        "1. ?¸ì Â·?™ì ?¬í•­ ?™ìƒ?•ë³´ ?±ëª… ?ê¸¸??,
        "2. ì¶?ê²?????ê²°ì„ ì§€ê°?ì¡°í‡´ ?†ìŒ",
        "3. ????ê²???êµê³¼?°ìˆ˜???˜ì—¬ê¸°ê? êµë‚´",
        "5. ì°½ì˜??ì²´í—˜?œë™?í™© ?ìœ¨?œë™ ?™ì•„ë¦¬í™œ??ì§„ë¡œ?œë™",
        "ë´‰ì‚¬?œë™ ì§€??‚¬???˜ê²½?•í™” 20?œê°„",
        "êµê³¼?™ìŠµë°œë‹¬?í™© ?˜í•™ ë¬¼ë¦¬ ?±ì·¨???°ìˆ˜",
        "?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­ ê±´ì¶• ?¬ë£Œ êµ¬ì¡° ë¶„ì„ ?„ë¡œ?íŠ¸",
        "?…ì„œ?œë™?í™© ?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬ ?¬ìš©??ê²½í—˜ ë³´ì™„",
    ]

    pages: list[dict[str, object]] = []
    elements: list[dict[str, object]] = []
    for idx, text in enumerate(page_texts, start=1):
        element_id = f"page-{idx}-table-0"
        pages.append({"page_number": idx, "width": 595.0, "height": 842.0, "element_ids": [element_id]})
        elements.append(
            {
                "element_id": element_id,
                "page_number": idx,
                "element_type": "table",
                "raw_text": text,
                "table_rows": [
                    {
                        "row_index": 0,
                        "cells": [
                            {
                                "cell_id": f"row-{idx}-0",
                                "row_index": 0,
                                "column_index": 0,
                                "text": text,
                            }
                        ],
                    }
                ],
            }
        )

    return ParsedDocumentPayload(
        parser_name="neis",
        source_extension=".pdf",
        page_count=len(page_texts),
        word_count=1500,
        content_text=" ".join(page_texts),
        content_markdown="",
        metadata={
            "normalized_artifact": {
                "schema_version": "test",
                "source_file": "sample.pdf",
                "parser_name": "neis",
                "page_count": len(page_texts),
                "pages": pages,
                "elements": elements,
            }
        },
        chunks=[
            ParsedChunkPayload(
                chunk_index=0,
                page_number=1,
                char_start=0,
                char_end=120,
                token_estimate=40,
                content_text=page_texts[0],
            )
        ],
        raw_artifact={"pages": [{"page_number": idx + 1, "text": ""} for idx in range(len(page_texts))]},
        masked_artifact={"pages": [{"page_number": idx + 1, "masked_text": ""} for idx in range(len(page_texts))]},
        parse_confidence=0.88,
        needs_review=False,
    )


def test_normalized_sections_and_evidence_bank_cover_required_sections() -> None:
    parsed = _build_full_section_payload()
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        analysis_artifact=None,
    )

    assert canonical is not None
    coverage = canonical.get("section_coverage") or {}
    assert coverage.get("missing_sections") == []
    assert canonical.get("quality_gates", {}).get("reanalysis_required") is False

    evidence_bank = canonical.get("evidence_bank") or []
    assert len(evidence_bank) >= 10
    unique_pages = {int(item.get("page") or 0) for item in evidence_bank}
    assert len({page for page in unique_pages if page > 0}) >= 6
    sample = evidence_bank[0]
    for key in ("page", "section", "normalized_section", "quote", "major_relevance", "process_elements", "confidence"):
        assert key in sample


def test_normalized_artifact_fallback_extracts_pages_when_raw_masked_empty() -> None:
    parsed = _build_normalized_artifact_only_payload()
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "fallback", "summary": "?”ì•½"},
        analysis_artifact=None,
    )

    assert canonical is not None
    coverage = canonical.get("section_coverage") or {}
    missing = coverage.get("missing_sections") or []
    assert "student_info" not in missing
    assert "grades_subjects" not in missing
    assert "subject_special_notes" not in missing
    assert "behavior_general_comments" not in missing
    assert canonical.get("evidence_bank")


def test_structure_contradiction_guard_removes_conflicting_weak_sections() -> None:
    parsed = _build_full_section_payload()
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        analysis_artifact=None,
    )
    assert canonical is not None
    canonical["weak_or_missing_sections"] = [
        {"section": "êµê³¼?™ìŠµë°œë‹¬?í™©", "status": "missing", "evidence": []},
    ]
    canonical["section_classification"]["grades_subjects"]["density"] = 1.0

    structure = build_student_record_structure_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "?”ì•½"},
        canonical_schema=canonical,
    )

    assert structure is not None
    assert "êµê³¼?™ìŠµë°œë‹¬?í™©" not in structure["weak_sections"]
    assert structure["contradiction_check"]["passed"] is False

