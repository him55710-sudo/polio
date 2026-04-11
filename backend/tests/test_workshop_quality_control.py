from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from unifoli_api.main import app
from unifoli_api.services.quality_control import (
    QUALITY_CONTROL_SCHEMA_VERSION,
    build_quality_control_metadata,
    resolve_advanced_features,
)
from unifoli_api.services.safety_guard import SafetyFlag, run_safety_check
from unifoli_api.services.workshop_render_service import _build_safe_artifact
from backend.tests.auth_helpers import auth_headers


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/projects",
        json={
            "title": f"Workshop QC {uuid4()}",
            "description": "Workshop quality-control test project.",
            "target_university": "Quality University",
            "target_major": "Education",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _post_long_message(client: TestClient, workshop_id: str, index: int, headers: dict[str, str]) -> None:
    message = (
        f"{index}ë²ˆì§¸ ?Œí¬???…ë ¥?…ë‹ˆ?? ?™ìƒ???¤ì œë¡??´ë³¸ ?œë™ê³?êµê³¼ ê°œë… ?°ê²°??ê¸¸ê²Œ ?¤ëª…?´ì„œ "
        f"?„ì¬ ?˜ì??ì„œ ê°€?¥í•œ ?êµ¬ ë§¥ë½??ì¶©ë¶„???•ë³´?©ë‹ˆ?? "
        f"?˜í–‰ ê°€?¥ì„±, ê´€ì°??¬ì¸?? ê¸°ë¡ ë¬¸ì¥ ?„ë³´ë¥?ëª¨ë‘ ?•ë¦¬?˜ë ¤??ëª©ì ?…ë‹ˆ??"
    )
    response = client.post(
        f"/api/v1/workshops/{workshop_id}/messages",
        json={"message": message},
        headers=headers,
    )
    assert response.status_code == 200


def _extract_event_payload(raw_stream: str, event_name: str) -> dict[str, object]:
    for block in raw_stream.split("\n\n"):
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines or lines[0] != f"event: {event_name}":
            continue
        data_line = next((line for line in lines if line.startswith("data: ")), None)
        if data_line is None:
            continue
        return json.loads(data_line.removeprefix("data: "))
    raise AssertionError(f"Event not found: {event_name}")


def test_workshop_quality_level_changes_choices_and_requirements() -> None:
    with TestClient(app) as client:
        headers = auth_headers("workshop-quality-user")
        project_id = _create_project(client, headers)

        create_response = client.post(
            "/api/v1/workshops",
            json={"project_id": project_id, "quality_level": "low"},
            headers=headers,
        )
        assert create_response.status_code == 201
        create_payload = create_response.json()
        assert create_payload["session"]["quality_level"] == "low"
        assert create_payload["quality_level_info"]["label"] == "?ˆì „??
        assert create_payload["render_requirements"]["minimum_reference_count"] == 0
        assert any(choice["label"] == "?µì‹¬ ê°œë…ë¶€???•ë¦¬" for choice in create_payload["starter_choices"])

        workshop_id = create_payload["session"]["id"]
        update_response = client.patch(
            f"/api/v1/workshops/{workshop_id}/quality-level",
            json={"quality_level": "high"},
            headers=headers,
        )
        assert update_response.status_code == 200
        update_payload = update_response.json()
        assert update_payload["session"]["quality_level"] == "high"
        assert update_payload["quality_level_info"]["label"] == "?¬í™”??
        assert update_payload["render_requirements"]["minimum_reference_count"] == 1
        assert any(choice["label"] == "?¬í™” ì§ˆë¬¸ ì¢íˆê¸? for choice in update_payload["starter_choices"])


def test_high_quality_render_requires_reference_before_rendering() -> None:
    with TestClient(app) as client:
        headers = auth_headers("workshop-high-render-user")
        project_id = _create_project(client, headers)
        workshop_response = client.post(
            "/api/v1/workshops",
            json={"project_id": project_id, "quality_level": "high"},
            headers=headers,
        )
        assert workshop_response.status_code == 201
        workshop_id = workshop_response.json()["session"]["id"]

        for index in range(5):
            _post_long_message(client, workshop_id, index, headers)

        render_response = client.post(
            f"/api/v1/workshops/{workshop_id}/render",
            json={"force": False},
            headers=headers,
        )
        assert render_response.status_code == 422
        detail = render_response.json()["detail"]
        assert detail["minimum_reference_count"] == 1
        assert "ì°¸ê³ ?ë£Œ" in " ".join(detail["missing"])


def test_workshop_render_persists_quality_control_metadata() -> None:
    with TestClient(app) as client:
        headers = auth_headers("workshop-render-user")
        project_id = _create_project(client, headers)
        workshop_response = client.post(
            "/api/v1/workshops",
            json={"project_id": project_id, "quality_level": "mid"},
            headers=headers,
        )
        assert workshop_response.status_code == 201
        workshop_id = workshop_response.json()["session"]["id"]

        for index in range(4):
            _post_long_message(client, workshop_id, index, headers)

        render_response = client.post(
            f"/api/v1/workshops/{workshop_id}/render",
            json={"force": False},
            headers=headers,
        )
        assert render_response.status_code == 200
        artifact_id = render_response.json()["artifact_id"]

        token_response = client.post(f"/api/v1/workshops/{workshop_id}/stream-token", headers=headers)
        assert token_response.status_code == 200
        stream_token = token_response.json()["stream_token"]

        stream_response = client.get(
            f"/api/v1/workshops/{workshop_id}/events",
            params={"stream_token": stream_token, "artifact_id": artifact_id},
        )
        assert stream_response.status_code == 200
        assert "event: artifact.ready" in stream_response.text

        artifact_payload = _extract_event_payload(stream_response.text, "artifact.ready")
        assert artifact_payload["report_markdown"].startswith("## ?êµ¬ ë³´ê³ ??)
        assert artifact_payload["quality_control"]["requested_level"] == "mid"
        assert artifact_payload["quality_control"]["applied_level"] in {"low", "mid"}

        workshop_state = client.get(f"/api/v1/workshops/{workshop_id}", headers=headers)
        assert workshop_state.status_code == 200
        latest_artifact = workshop_state.json()["latest_artifact"]
        assert latest_artifact["quality_control_meta"]["requested_level"] == "mid"
        assert latest_artifact["quality_control_meta"]["checks"]


def test_safety_guard_detects_ungrounded_high_risk_output() -> None:
    result = run_safety_check(
        report_markdown=(
            "?‘ì??•™ ê°œë…???œìš©??ì§ì ‘ ?¤í—˜??ì§„í–‰?ˆê³ , 200ëª??¤ë¬¸ ê²°ê³¼ 83%ê°€ ê¸ì •?ì´?ˆë‹¤ê³??•ë¦¬?ˆë‹¤."
        ),
        teacher_summary="?™ìƒ???€???°êµ¬???˜ì????¤í—˜ê³??€ê·œëª¨ ?¤ë¬¸???˜í–‰??ê²ƒìœ¼ë¡?ë³´ì´ê²??‘ì„±?ˆë‹¤.",
        requested_level="high",
        turn_count=1,
        reference_count=0,
        turns_text="?™ìƒ?€ ê´€??ì£¼ì œë¥??•í•˜ê³??¶ë‹¤ê³ ë§Œ ë§í–ˆ??",
        references_text="",
    )

    assert result.downgraded is True
    assert result.recommended_level == "low"
    assert SafetyFlag.FABRICATION_RISK.value in result.flags
    assert SafetyFlag.FEASIBILITY_RISK.value in result.flags
    assert result.checks["fabrication"].unsupported_count >= 2


def test_quality_control_schema_tracks_guardrail_and_advanced_metadata() -> None:
    metadata = build_quality_control_metadata(
        requested_level="high",
        applied_level="mid",
        turn_count=4,
        reference_count=1,
        safety_score=72,
        downgraded=True,
        summary="?ˆì „??ê¸°ì????°ë¼ ?˜ì???ì¡°ì •?ˆìŠµ?ˆë‹¤.",
        advanced_features_requested=True,
        advanced_features_applied=False,
        advanced_features_reason="?ˆì „ ?¬ì‘??ê³¼ì •?ì„œ ê³ ê¸‰ ?•ì¥???œê±°?ˆìŠµ?ˆë‹¤.",
    )

    assert metadata["schema_version"] == QUALITY_CONTROL_SCHEMA_VERSION
    assert metadata["requested_level"] == "high"
    assert metadata["applied_level"] == "mid"
    assert metadata["safety_posture"]
    assert metadata["authenticity_policy"]
    assert metadata["hallucination_guardrail"]
    assert metadata["advanced_features_requested"] is True
    assert metadata["advanced_features_applied"] is False


def test_same_context_renders_different_depth_by_quality_level() -> None:
    turns = [
        SimpleNamespace(
            id="turn-1",
            turn_type="message",
            query="?™êµ ?˜ì—… ?œê°„??ë¯¸ì„¸ë¨¼ì? ì£¼ì œë¥?ì¡°ì‚¬?˜ë©° ì§€??³„ ?˜ì¹˜ë¥?ë¹„êµ??ë´¤ë‹¤.",
            action_payload=None,
        )
    ]
    references = [
        SimpleNamespace(
            id="ref-1",
            source_type="manual_note",
            text_content="?˜ê²½ë¶€ ê³µê°œ ?ë£Œ?ì„œ ì§€??³„ ë¯¸ì„¸ë¨¼ì? ?ë„ ë¹„êµ ?œë? ?•ì¸?ˆë‹¤.",
        )
    ]

    low = _build_safe_artifact(
        turns=turns,
        references=references,
        target_major="?˜ê²½ê³µí•™",
        target_university="Quality University",
        quality_level="low",
    )
    mid = _build_safe_artifact(
        turns=turns,
        references=references,
        target_major="?˜ê²½ê³µí•™",
        target_university="Quality University",
        quality_level="mid",
    )
    high = _build_safe_artifact(
        turns=turns,
        references=references,
        target_major="?˜ê²½ê³µí•™",
        target_university="Quality University",
        quality_level="high",
    )

    assert "?´ë²ˆ ?™ê¸° ?ˆì— ê°€?¥í•œ ?˜í–‰" in low["report_markdown"]
    assert "ê°„ë‹¨???´ì„ê³??¤ìŒ ?¨ê³„" in mid["report_markdown"]
    assert "?¤ì œ ë§¥ë½ ê¸°ë°˜ ?¬í™” ì§ˆë¬¸" in high["report_markdown"]
    assert low["report_markdown"] != mid["report_markdown"] != high["report_markdown"]


def test_advanced_features_require_high_level_and_reference_support() -> None:
    enabled, reason = resolve_advanced_features(requested=True, quality_level="mid", reference_count=3)
    assert enabled is False
    assert "?œì??? in reason

    enabled, reason = resolve_advanced_features(requested=True, quality_level="high", reference_count=0)
    assert enabled is False
    assert "ì°¸ê³ ?ë£Œ 1ê°??´ìƒ" in reason

    enabled, reason = resolve_advanced_features(requested=True, quality_level="high", reference_count=2)
    assert enabled is True
    assert "ê³ ê¸‰ ?•ì¥" in reason

