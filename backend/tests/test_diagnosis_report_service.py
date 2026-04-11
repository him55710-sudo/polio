from __future__ import annotations

import json
from types import SimpleNamespace

from unifoli_api.schemas.diagnosis import (
    ConsultantDiagnosisEvidenceItem,
    ConsultantDiagnosisReport,
    DiagnosisResultPayload,
)
from unifoli_api.services import diagnosis_report_service as report_service


def _minimal_result() -> DiagnosisResultPayload:
    return DiagnosisResultPayload.model_validate(
        {
            "headline": "기초 진단 헤드라인",
            "strengths": ["탐구 주제의 연속성이 보입니다."],
            "gaps": ["근거 문장과 인용 연결을 더 명확히 해야 합니다."],
            "recommended_focus": "근거-주장 매핑 강화",
            "risk_level": "warning",
            "next_actions": ["핵심 주장 3개에 근거 출처를 연결하세요."],
            "recommended_topics": ["전공 연계 심화 탐구"],
            "citations": [],
        }
    )


def test_humanize_section_title_is_korean() -> None:
    assert report_service._humanize_section_title("executive_summary") == "핵심 요약"  # noqa: SLF001
    assert report_service._humanize_section_title("strength_analysis") == "강점 분석"  # noqa: SLF001
    assert report_service._humanize_section_title("roadmap") == "실행 로드맵"  # noqa: SLF001


def test_build_failed_report_payload_is_valid_schema() -> None:
    payload_text = report_service._build_failed_report_payload(  # noqa: SLF001
        run=SimpleNamespace(id="run-failed"),
        project=SimpleNamespace(id="project-failed", title="테스트 프로젝트"),
        report_mode="compact",
        template_id="consultant_diagnosis_compact",
    )
    parsed = ConsultantDiagnosisReport.model_validate_json(payload_text)
    assert parsed.title == "테스트 프로젝트 전문 컨설턴트 진단"
    assert parsed.sections[0].id == "generation_failed"


def test_diverse_evidence_items_prefers_unique_pages() -> None:
    seed = [
        ConsultantDiagnosisEvidenceItem(
            source_label="학생부 p.1",
            page_number=1,
            excerpt="기존 근거 1",
            relevance_score=1.0,
            support_status="verified",
        )
    ]
    evidence_bank = [
        {"anchor_id": "a1", "page": 1, "quote": "근거 문장 1", "confidence": 0.9, "section": "교과"},
        {"anchor_id": "a2", "page": 2, "quote": "근거 문장 2", "confidence": 0.8, "section": "창체"},
        {"anchor_id": "a3", "page": 3, "quote": "근거 문장 3", "confidence": 0.7, "section": "진로"},
    ]
    diversified = report_service._build_diverse_evidence_items(  # noqa: SLF001
        evidence_items=seed,
        evidence_bank=evidence_bank,
        limit=5,
    )
    pages = {item.page_number for item in diversified if item.page_number}
    assert len(pages) >= 3
