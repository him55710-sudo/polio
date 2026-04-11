from __future__ import annotations

from tests.smoke.helpers import REPO_ROOT  # noqa: F401  # Ensures backend packages are on sys.path.

from unifoli_domain.enums import RenderFormat
from unifoli_render.template_registry import (
    build_provenance_appendix_lines,
    get_default_template_id,
    get_template,
    list_templates,
)


def test_hwpx_default_template_stays_submission_friendly() -> None:
    default_id = get_default_template_id(RenderFormat.HWPX)
    template = get_template(default_id, render_format=RenderFormat.HWPX)

    assert template.id == "activity_summary_school"
    assert template.category == "school_record"
    assert template.visual_priority == "low"
    assert template.density == "light"


def test_hwpx_template_catalog_excludes_presentation_forward_templates() -> None:
    hwpx_template_ids = {template.id for template in list_templates(render_format=RenderFormat.HWPX)}

    assert "activity_summary_school" in hwpx_template_ids
    assert "presentation_minimal" not in hwpx_template_ids
    assert "presentation_visual_focus" not in hwpx_template_ids
    assert "proposal_pitch" not in hwpx_template_ids


def test_provenance_appendix_hides_internal_notes_when_policy_requests_it() -> None:
    lines = build_provenance_appendix_lines(
        evidence_map={
            "Concept claim": {
                "evidence": "Student compared two datasets.",
                "source": "turn:internal-123",
            }
        },
        authenticity_log_lines=[
            "Internal workshop prompt with raw note details.",
            "Second internal grounding note.",
        ],
        hide_internal=True,
    )

    assert any("Workshop conversation" in line for line in lines)
    assert any("retained internally" in line for line in lines)
    assert all("turn:internal-123" not in line for line in lines)
    assert all("Internal workshop prompt with raw note details." not in line for line in lines)


def test_provenance_appendix_keeps_raw_internal_notes_for_internal_exports() -> None:
    lines = build_provenance_appendix_lines(
        evidence_map={
            "Concept claim": {
                "evidence": "Student compared two datasets.",
                "source": "turn:internal-123",
            }
        },
        authenticity_log_lines=[
            "Internal workshop prompt with raw note details.",
        ],
        hide_internal=False,
    )

    assert any("turn:internal-123" in line for line in lines)
    assert any("Workshop note: Internal workshop prompt with raw note details." in line for line in lines)
