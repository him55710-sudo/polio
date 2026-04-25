from unifoli_api.services.workshop_graph_service import (
    WorkshopGraphEvent,
    WorkshopGraphPhase,
    WorkshopGraphState,
    run_workshop_graph_step,
)


def test_workshop_graph_step_moves_topic_selection_to_outline_generation() -> None:
    state = WorkshopGraphState(project_id="project-1", workshop_id="workshop-1")
    result = run_workshop_graph_step(
        state,
        WorkshopGraphEvent(type="topic_selected", payload={"topic_id": "topic-1"}),
    )

    assert result.state.phase == WorkshopGraphPhase.OUTLINE_GENERATION
    assert result.state.selected_topic_id == "topic-1"
    assert result.emitted_events[0].type == "topic_selected"


def test_workshop_graph_step_keeps_patch_pending_until_review_event() -> None:
    state = WorkshopGraphState(phase=WorkshopGraphPhase.PATCH_GENERATION)
    result = run_workshop_graph_step(
        state,
        WorkshopGraphEvent(type="patch_generated", payload={"patch": {"patchId": "patch-1"}}),
    )

    assert result.state.phase == WorkshopGraphPhase.PATCH_REVIEW
    assert result.state.pending_patch == {"patchId": "patch-1"}
    assert result.actions == [
        {"type": "show_patch_review", "patch": {"patchId": "patch-1"}},
        {"type": "wait_for_user_approval"},
    ]


def test_workshop_graph_step_clears_patch_after_acceptance() -> None:
    state = WorkshopGraphState(
        phase=WorkshopGraphPhase.PATCH_REVIEW,
        pending_patch={"patchId": "patch-1"},
    )
    result = run_workshop_graph_step(state, WorkshopGraphEvent(type="patch_accepted"))

    assert result.state.phase == WorkshopGraphPhase.PATCH_APPLIED
    assert result.state.pending_patch is None
