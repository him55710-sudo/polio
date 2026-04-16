from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from unifoli_api.core.config import Settings
from unifoli_api.services.diagnosis_copilot_service import build_diagnosis_copilot_brief
from unifoli_api.services.diagnosis_runtime_service import combine_project_text, run_diagnosis_run
from unifoli_api.services.diagnosis_service import DiagnosisResult


def _build_minimal_result(headline: str) -> DiagnosisResult:
    return DiagnosisResult(
        headline=headline,
        strengths=["grounded strength"],
        gaps=["grounded gap"],
        recommended_focus="next grounded focus",
        risk_level="warning",
    )


def test_combine_project_text_returns_structured_error_when_documents_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "unifoli_api.services.diagnosis_runtime_service.list_documents_for_project",
        lambda db, project_id: [],
    )

    try:
        combine_project_text("project-empty", db=SimpleNamespace())
    except HTTPException as exc:
        assert exc.status_code == 400
        assert isinstance(exc.detail, dict)
        assert exc.detail["code"] == "DIAGNOSIS_INPUT_EMPTY"
        assert exc.detail["stage"] == "combine_project_text"
    else:  # pragma: no cover - defensive branch
        raise AssertionError("combine_project_text should raise when no documents are available")


def test_runtime_persists_artifacts_and_survives_trace_persistence_failure(monkeypatch) -> None:
    settings = Settings(llm_provider="ollama", ollama_model="gemma4-test", gemini_api_key=None)
    run = SimpleNamespace(
        id="run-trace-failure",
        policy_flags=[],
        review_tasks=[],
        result_payload=None,
        status="PENDING",
        error_message=None,
        project_id="project-trace-failure",
    )
    project = SimpleNamespace(id="project-trace-failure", title="diagnosis project", target_major="Computer Science")
    owner = SimpleNamespace(id="owner-trace-failure", career="AI Engineering")
    document = SimpleNamespace(
        id="doc-trace-failure",
        sha256="sha-doc-trace-failure",
        content_text="grounded evidence text for persisted diagnosis artifacts",
        content_markdown="",
        stored_path=None,
        source_extension=".pdf",
        parse_metadata={
            "student_record_canonical": {
                "section_coverage": {"missing_sections": ["behavior_opinion"]},
                "major_alignment_hints": [{"hint": "Robotics inquiry aligns with engineering majors."}],
                "timeline_signals": [{"signal": "Grade 2 research activity deepened prototype testing."}],
            }
        },
    )

    class _FakeDB:
        def __init__(self) -> None:
            self.commit_count = 0
            self.rollback_count = 0

        def get(self, model, user_id):  # noqa: ANN001, ARG002
            return owner

        def add(self, obj):  # noqa: ANN001, ARG002
            return None

        def commit(self):
            self.commit_count += 1

        def refresh(self, obj):  # noqa: ANN001, ARG002
            return None

        def rollback(self):
            self.rollback_count += 1

        def scalar(self, stmt):  # noqa: ANN001, ARG002
            return None

    fake_db = _FakeDB()

    async def fake_evaluate_student_record(**kwargs):  # noqa: ANN003
        return _build_minimal_result("artifact-rich diagnosis")

    async def fake_extract_semantic_diagnosis(**kwargs):  # noqa: ANN003
        return None

    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.get_settings", lambda: settings)
    monkeypatch.setattr(
        "unifoli_api.services.diagnosis_runtime_service._diagnosis_llm_strategy",
        lambda: {
            "requested_llm_provider": "ollama",
            "requested_llm_model": "gemma4-test",
            "actual_llm_provider": "ollama",
            "actual_llm_model": "gemma4-test",
            "llm_profile_used": "standard",
            "should_use_llm": True,
            "fallback_used": False,
            "fallback_reason": None,
        },
    )
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.get_run_with_relations", lambda db, run_id: run)
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.get_project", lambda db, project_id, owner_user_id: project)
    monkeypatch.setattr(
        "unifoli_api.services.diagnosis_runtime_service.combine_project_text",
        lambda project_id, db: ([document], document.content_text),
    )
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.list_chunks_for_project", lambda db, project_id: [])
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.build_policy_scan_text", lambda documents: "")
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.detect_policy_flags", lambda text: [])
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.evaluate_student_record", fake_evaluate_student_record)
    monkeypatch.setattr("unifoli_api.services.diagnosis_scoring_service.extract_semantic_diagnosis", fake_extract_semantic_diagnosis)
    monkeypatch.setattr(
        "unifoli_api.services.diagnosis_runtime_service.create_response_trace",
        lambda db, **kwargs: (_ for _ in ()).throw(RuntimeError("trace persistence unavailable")),
    )
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.create_blueprint_from_signals", lambda db, project, diagnosis_run_id, signals: None)
    monkeypatch.setattr("unifoli_api.services.diagnosis_runtime_service.build_blueprint_signals", lambda **kwargs: {})

    completed = asyncio.run(
        run_diagnosis_run(
            fake_db,
            run_id="run-trace-failure",
            project_id="project-trace-failure",
            owner_user_id="owner-trace-failure",
            fallback_target_university="Test Univ",
            fallback_target_major="Computer Science",
        )
    )

    payload = DiagnosisResult.model_validate_json(completed.result_payload)
    assert completed.status == "COMPLETED"
    assert payload.response_trace_id is None
    assert payload.diagnosis_result_json is not None
    assert payload.diagnosis_summary_json is not None
    assert payload.diagnosis_report_markdown
    assert payload.chatbot_context_json is not None
    assert payload.chatbot_context_json["major_alignment_hints"] == ["Robotics inquiry aligns with engineering majors."]
    assert payload.chatbot_context_json["missing_sections"] == ["behavior_opinion"]
    assert "artifact-rich diagnosis" in payload.diagnosis_report_markdown
    assert completed.status_message.startswith("Diagnosis completed")
    assert fake_db.rollback_count >= 1


def test_copilot_brief_uses_persisted_artifact_bundle() -> None:
    payload = DiagnosisResult.model_validate(
        {
            "headline": "Grounded diagnosis headline",
            "strengths": ["evidence-backed strength"],
            "gaps": ["missing evidence gap"],
            "recommended_focus": "next focus",
            "risk_level": "warning",
            "diagnosis_summary_json": {
                "headline": "Grounded diagnosis headline",
                "recommended_focus": "next focus",
                "strengths": ["evidence-backed strength"],
            },
            "chatbot_context_json": {
                "key_strengths": ["evidence-backed strength"],
                "key_weaknesses": ["missing evidence gap"],
                "target_risks": ["target risk"],
                "recommended_activity_topics": ["robotics ethics inquiry"],
                "caution_points": ["needs more verified evidence"],
                "evidence_references": [
                    {
                        "source_label": "Student record",
                        "page_number": 2,
                        "excerpt": "Documented robotics experiment reflection",
                        "relevance_score": 0.81,
                    }
                ],
            },
        }
    )

    class _FakeDB:
        def scalar(self, stmt):  # noqa: ANN001, ARG002
            return SimpleNamespace(result_payload=payload.model_dump_json())

    brief = build_diagnosis_copilot_brief(_FakeDB(), project_id="project-1")

    assert "[Diagnosis Artifact Brief]" in brief
    assert "Grounded diagnosis headline" in brief
    assert "robotics ethics inquiry" in brief
    assert "Student record p.2" in brief


def test_copilot_brief_fallback_text_is_readable_without_artifact_bundle() -> None:
    payload = DiagnosisResult.model_validate(
        {
            "headline": "Grounded diagnosis headline",
            "strengths": ["evidence-backed strength"],
            "gaps": ["missing evidence gap"],
            "recommended_focus": "next focus",
            "risk_level": "warning",
            "next_actions": ["build a better evidence trail"],
            "recommended_topics": ["robotics ethics inquiry"],
            "fallback_used": True,
            "citations": [
                {
                    "source_label": "Student record",
                    "page_number": 3,
                    "excerpt": "Documented lab reflection",
                    "relevance_score": 0.74,
                }
            ],
            "document_quality": {
                "source_mode": "mixed",
                "parse_reliability_score": 62,
                "parse_reliability_band": "medium",
                "needs_review": True,
                "needs_review_documents": 1,
                "total_records": 12,
                "total_word_count": 420,
                "narrative_density": 0.58,
                "evidence_density": 0.61,
                "summary": "Document extraction needs manual review.",
            },
        }
    )

    class _FakeDB:
        def scalar(self, stmt):  # noqa: ANN001, ARG002
            return SimpleNamespace(result_payload=payload.model_dump_json())

        def scalars(self, stmt):  # noqa: ANN001, ARG002
            return []

    brief = build_diagnosis_copilot_brief(_FakeDB(), project_id="project-2")

    assert "[Diagnosis Copilot Brief]" in brief
    assert "Grounded diagnosis headline" in brief
    assert "manual review" in brief
    assert "deterministic fallback mode" in brief
    assert "Student record p.3" in brief
