from __future__ import annotations

from polio_api.core.config import Settings
from polio_api.core.llm import OllamaClient, get_pdf_analysis_llm_client
from polio_api.services.pdf_analysis_service import (
    build_pdf_analysis_metadata,
    build_student_record_canonical_metadata,
    build_student_record_structure_metadata,
)
from polio_ingest.models import ParsedChunkPayload, ParsedDocumentPayload


class _FakePdfLLM:
    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        return response_model(
            summary="문서의 핵심 흐름이 페이지별로 비교적 명확하게 확인됩니다.",
            key_points=["활동 동기", "과정 기록", "결과와 성찰"],
            page_insights=[
                {"page_number": 1, "summary": "1페이지에는 활동 배경과 목표가 정리되어 있습니다."},
                {"page_number": 2, "summary": "2페이지에는 수행 과정과 결과가 이어집니다."},
            ],
            evidence_gaps=["일부 수치 근거는 원문 재확인이 필요합니다."],
        )


class _TextFallbackPdfLLM:
    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        raise RuntimeError("json schema response unsupported")

    async def stream_chat(self, prompt, system_instruction=None, temperature=0.5):  # noqa: ANN001
        yield (
            "## PDF 페이지별 핵심 요약\n"
            "전체 요약: 문서 흐름을 페이지별로 검토했습니다.\n"
            "1페이지: 활동 배경과 목표가 정리되어 있습니다.\n"
            "2페이지: 수행 과정과 결과가 이어집니다.\n"
            "근거 부족: 일부 수치는 원문 재확인이 필요합니다.\n"
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
        content_text="1페이지 활동 배경과 목표. 2페이지 수행 과정과 결과.",
        content_markdown="## Page 1\n활동 배경과 목표\n\n## Page 2\n수행 과정과 결과",
        metadata={},
        chunks=[
            ParsedChunkPayload(
                chunk_index=0,
                page_number=1,
                char_start=0,
                char_end=30,
                token_estimate=8,
                content_text="활동 배경과 목표",
            )
        ],
        masked_artifact={
            "pages": [
                {"page_number": 1, "masked_text": "활동 배경과 목표가 상세히 기록되어 있습니다."},
                {"page_number": 2, "masked_text": "수행 과정과 결과, 다음 계획이 포함되어 있습니다."},
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
            "2학년 1학기 교과학습발달상황 수학 과목에서 탐구 프로젝트를 수행함. "
            "세부능력 및 특기사항에 문제 해결 과정과 피드백이 기록됨. "
            "창의적 체험활동 동아리와 봉사활동, 진로활동이 이어졌고 진로 희망 학과와 연계함. "
            "독서 활동과 행동특성 및 종합의견이 포함됨."
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
                content_text="교과학습발달상황 수학 과목 탐구 프로젝트",
            )
        ],
        raw_artifact={
            "pages": [
                {
                    "page_number": 1,
                    "text": "2학년 1학기 교과학습발달상황 수학 과목 탐구 프로젝트 세부능력 및 특기사항",
                },
                {
                    "page_number": 2,
                    "text": "창의적 체험활동 동아리 봉사활동 진로활동 희망 학과 연계",
                },
                {
                    "page_number": 3,
                    "text": "독서 활동 행동특성 및 종합의견",
                },
            ]
        },
        masked_artifact={
            "pages": [
                {
                    "page_number": 1,
                    "masked_text": "2학년 1학기 교과학습발달상황 수학 과목 탐구 프로젝트 세부능력 및 특기사항",
                },
                {
                    "page_number": 2,
                    "masked_text": "창의적 체험활동 동아리 봉사활동 진로활동 희망 학과 연계",
                },
                {
                    "page_number": 3,
                    "masked_text": "독서 활동 행동특성 및 종합의견",
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
    monkeypatch.setattr("polio_api.services.pdf_analysis_service.get_settings", lambda: settings)
    monkeypatch.setattr("polio_api.services.pdf_analysis_service.get_pdf_analysis_llm_client", lambda: _FakePdfLLM())

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
    monkeypatch.setattr("polio_api.services.pdf_analysis_service.get_settings", lambda: settings)
    monkeypatch.setattr("polio_api.services.pdf_analysis_service.get_pdf_analysis_llm_client", lambda: _FailingPdfLLM())

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
    monkeypatch.setattr("polio_api.services.pdf_analysis_service.get_settings", lambda: settings)
    monkeypatch.setattr("polio_api.services.pdf_analysis_service.get_pdf_analysis_llm_client", lambda: _TextFallbackPdfLLM())

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
    monkeypatch.setattr("polio_api.core.llm.get_settings", lambda: settings)

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
        pdf_analysis={"engine": "llm", "summary": "요약"},
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
        pdf_analysis={"engine": "fallback", "summary": "휴리스틱"},
        analysis_artifact=None,
    )

    assert canonical is not None
    assert canonical["document_confidence"] < 0.8
    assert canonical["uncertainties"]
    uncertainty_messages = [str(item.get("message") or "") for item in canonical["uncertainties"]]
    assert any("confidence" in message or "검토" in message for message in uncertainty_messages)


def test_student_record_structure_bridge_uses_canonical_schema() -> None:
    parsed = _build_student_record_payload()
    canonical = build_student_record_canonical_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "요약"},
        analysis_artifact=None,
    )
    structure = build_student_record_structure_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "요약"},
        canonical_schema=canonical,
    )

    assert structure is not None
    assert structure["section_density"]["교과학습발달상황"] > 0
    assert structure["timeline_signals"]
    assert "subject_major_alignment_signals" in structure


def _build_full_section_payload() -> ParsedDocumentPayload:
    pages = [
        {"page_number": 1, "text": "인적사항 성명 홍길동 학교명 테스트고등학교"},
        {"page_number": 2, "text": "출결상황 결석 지각 조퇴 없음"},
        {"page_number": 3, "text": "수상경력 수상명 과학탐구발표대회 수여기관 교내"},
        {"page_number": 4, "text": "창의적 체험활동 동아리활동 진로활동 지속가능 건축 탐구"},
        {"page_number": 5, "text": "봉사활동 지역사회 환경정화 봉사시간 20시간"},
        {"page_number": 6, "text": "교과학습발달상황 과목 수학 물리 성취도 우수"},
        {"page_number": 7, "text": "세부능력 및 특기사항 건축 재료 구조 분석 프로젝트 수행"},
        {"page_number": 8, "text": "독서활동상황 행동특성 및 종합의견 사용자 경험 공간 인문 보완"},
        {"page_number": 9, "text": "교과학습발달상황 과목 영어 과학 성취도 우수"},
        {"page_number": 10, "text": "세부능력 및 특기사항 기후 대응 건축 설계 확장 활동"},
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
        "1. 인적·학적사항 학생정보 성명 홍길동",
        "2. 출 결 상 황 결석 지각 조퇴 없음",
        "3. 수 상 경 력 교과우수상 수여기관 교내",
        "5. 창의적 체험활동상황 자율활동 동아리활동 진로활동",
        "봉사활동 지역사회 환경정화 20시간",
        "교과학습발달상황 수학 물리 성취도 우수",
        "세부능력 및 특기사항 건축 재료 구조 분석 프로젝트",
        "독서활동상황 행동특성 및 종합의견 사용자 경험 보완",
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
        pdf_analysis={"engine": "llm", "summary": "요약"},
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
        pdf_analysis={"engine": "fallback", "summary": "요약"},
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
        pdf_analysis={"engine": "llm", "summary": "요약"},
        analysis_artifact=None,
    )
    assert canonical is not None
    canonical["weak_or_missing_sections"] = [
        {"section": "교과학습발달상황", "status": "missing", "evidence": []},
    ]
    canonical["section_classification"]["grades_subjects"]["density"] = 1.0

    structure = build_student_record_structure_metadata(
        parsed=parsed,
        pdf_analysis={"engine": "llm", "summary": "요약"},
        canonical_schema=canonical,
    )

    assert structure is not None
    assert "교과학습발달상황" not in structure["weak_sections"]
    assert structure["contradiction_check"]["passed"] is False
