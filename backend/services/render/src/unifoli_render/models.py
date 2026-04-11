from dataclasses import dataclass, field

from unifoli_domain.enums import RenderFormat
from unifoli_render.template_registry import RenderExportPolicy, RenderTemplate, get_template


@dataclass(slots=True)
class RenderBuildContext:
    project_id: str
    project_title: str
    draft_id: str
    draft_title: str
    render_format: RenderFormat
    content_markdown: str
    requested_by: str | None
    job_id: str
    visual_specs: list[dict] = field(default_factory=list)
    math_expressions: list[dict] = field(default_factory=list)
    evidence_map: dict[str, dict] = field(default_factory=dict)
    authenticity_log_lines: list[str] = field(default_factory=list)
    template_id: str | None = None
    export_policy: RenderExportPolicy = field(default_factory=RenderExportPolicy)

    def resolve_template(self) -> RenderTemplate:
        return get_template(self.template_id, render_format=self.render_format)


@dataclass(slots=True)
class RenderArtifact:
    absolute_path: str
    relative_path: str
    message: str
