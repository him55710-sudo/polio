from __future__ import annotations

from fastapi.testclient import TestClient

from unifoli_api.core.config import Settings
from unifoli_api.core.llm import OllamaClient, get_llm_client
from unifoli_api.main import app
from unifoli_api.schemas.guided_chat import TopicSuggestion
from backend.tests.auth_helpers import auth_headers

FIXED_GREETING = "?덈뀞?섏꽭?? ?대뼡 二쇱젣??蹂닿퀬?쒕? ?⑤낵源뚯슂?"


class _FakeGuidedChatLLM:
    def __init__(self, suggestion_count: int = 3):
        self.suggestion_count = suggestion_count

    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        suggestions = [
            TopicSuggestion(
                id=f"topic-{index + 1}",
                title=f"?뚯뒪??二쇱젣 {index + 1}",
                why_fit_student="?뺤씤??留λ씫 踰붿쐞 ?덉뿉???덉쟾?섍쾶 吏꾪뻾 媛?ν븳 二쇱젣?낅땲??",
                link_to_record_flow="湲곕줉 ?먮쫫怨??곌껐 媛?ν븳 踰붿쐞?먯꽌 ?쒖븞?쒕┰?덈떎.",
                link_to_target_major_or_university=None,
                novelty_point="湲곗〈 ?먮쫫??蹂댁닔?곸쑝濡??뺤옣?⑸땲??",
                caution_note=None,
            )
            for index in range(self.suggestion_count)
        ]
        return response_model(
            greeting=FIXED_GREETING,
            subject="?섑븰",
            suggestions=suggestions,
            evidence_gap_note=None,
        )


class _FailingGuidedChatLLM:
    async def generate_json(self, prompt, response_model, system_instruction=None, temperature=0.2):  # noqa: ANN001
        raise RuntimeError("forced failure")


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"title": "Guided Chat Test Project", "target_major": "?섑븰"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_local_env_without_gemini_key_falls_back_to_ollama(monkeypatch) -> None:
    settings = Settings(
        app_env="local",
        llm_provider="gemini",
        gemini_api_key=None,
        ollama_model="gemma",
    )
    monkeypatch.setattr("unifoli_api.core.llm.get_settings", lambda: settings)

    client = get_llm_client()

    assert isinstance(client, OllamaClient)
    assert client.model == "gemma"


def test_guided_chat_start_uses_exact_fixed_greeting() -> None:
    headers = auth_headers("guided-chat-start-user")
    with TestClient(app) as client:
        project_id = _create_project(client, headers)
        response = client.post(
            "/api/v1/guided-chat/start",
            headers=headers,
            json={"project_id": project_id},
        )

    assert response.status_code == 200
    assert response.json()["greeting"] == FIXED_GREETING


def test_topic_suggestions_always_return_exactly_three_items(monkeypatch) -> None:
    monkeypatch.setattr("unifoli_api.services.guided_chat_service.get_llm_client", lambda: _FakeGuidedChatLLM(suggestion_count=2))

    headers = auth_headers("guided-chat-suggestions-user")
    with TestClient(app) as client:
        project_id = _create_project(client, headers)
        response = client.post(
            "/api/v1/guided-chat/topic-suggestions",
            headers=headers,
            json={"project_id": project_id, "subject": "?섑븰"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["greeting"] == FIXED_GREETING
    assert len(payload["suggestions"]) == 3


def test_missing_diagnosis_data_returns_limited_context_note(monkeypatch) -> None:
    monkeypatch.setattr("unifoli_api.services.guided_chat_service.get_llm_client", lambda: _FailingGuidedChatLLM())

    headers = auth_headers("guided-chat-limited-context-user")
    with TestClient(app) as client:
        project_id = _create_project(client, headers)
        response = client.post(
            "/api/v1/guided-chat/topic-suggestions",
            headers=headers,
            json={"project_id": project_id, "subject": "?섑븰"},
        )

    assert response.status_code == 200
    payload = response.json()
    note = payload.get("evidence_gap_note") or ""
    assert note
    assert ("?쒗븳" in note) or ("遺議? in note)
    assert len(payload["suggestions"]) == 3


def test_topic_selection_returns_richer_starter_draft(monkeypatch) -> None:
    monkeypatch.setattr("unifoli_api.services.guided_chat_service.get_llm_client", lambda: _FakeGuidedChatLLM(suggestion_count=3))

    headers = auth_headers("guided-chat-selection-user")
    with TestClient(app) as client:
        project_id = _create_project(client, headers)
        suggestions_response = client.post(
            "/api/v1/guided-chat/topic-suggestions",
            headers=headers,
            json={"project_id": project_id, "subject": "?섑븰"},
        )
        assert suggestions_response.status_code == 200
        suggestions_payload = suggestions_response.json()
        selected_id = suggestions_payload["suggestions"][0]["id"]

        selection_response = client.post(
            "/api/v1/guided-chat/topic-selection",
            headers=headers,
            json={
                "project_id": project_id,
                "selected_topic_id": selected_id,
                "subject": "?섑븰",
                "suggestions": suggestions_payload["suggestions"],
            },
        )

    assert selection_response.status_code == 200
    payload = selection_response.json()
    starter = payload["starter_draft_markdown"]
    assert "## 利앷굅-?덉쟾 ?묒꽦 寃쎄퀎" in starter
    assert "## Evidence Memo" in starter
    assert "## ?꾩엯 臾몃떒(珥덉븞)" in starter
    assert isinstance(payload.get("state_summary"), dict)


