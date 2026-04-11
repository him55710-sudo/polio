from pathlib import Path

from unifoli_domain.enums import RenderFormat
from unifoli_render.formats.base import BaseRenderer
from unifoli_render.formats.hwpx_renderer import HwpxRenderer
from unifoli_render.formats.pdf_renderer import PdfRenderer
from unifoli_render.formats.pptx_renderer import PptxRenderer
from unifoli_render.models import RenderArtifact, RenderBuildContext


RENDERERS: dict[RenderFormat, type[BaseRenderer]] = {
    RenderFormat.PDF: PdfRenderer,
    RenderFormat.PPTX: PptxRenderer,
    RenderFormat.HWPX: HwpxRenderer,
}


def dispatch_render(context: RenderBuildContext, output_path: str | Path) -> RenderArtifact:
    renderer_cls = RENDERERS[context.render_format]
    renderer = renderer_cls()
    return renderer.render(context, output_path)
