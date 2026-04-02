from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from polio_render.formats.base import BaseRenderer
from polio_render.markdown import split_markdown_sections
from polio_render.models import RenderArtifact, RenderBuildContext
from polio_render.template_registry import build_provenance_appendix_lines
from polio_shared.paths import to_stored_path


class PdfRenderer(BaseRenderer):
    extension = ".pdf"
    implementation_level = "reportlab"

    def render(self, context: RenderBuildContext) -> RenderArtifact:
        output_path = self.prepare_output_path(context)
        self._build_pdf(context, output_path)

        relative_path = to_stored_path(output_path)
        message = "PDF renderer completed with ReportLab."
        return RenderArtifact(
            absolute_path=str(output_path),
            relative_path=relative_path,
            message=message,
        )

    def _build_pdf(self, context: RenderBuildContext, output_path) -> None:
        template = context.resolve_template()
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=54,
            bottomMargin=54,
            title=context.draft_title,
            author=context.requested_by or "polio backend",
        )

        styles = getSampleStyleSheet()
        accent = colors.HexColor(template.preview.accent_color)
        title_style = ParagraphStyle(
            "PolioTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            spaceAfter=10,
        )
        template_style = ParagraphStyle(
            "PolioTemplate",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=accent,
            spaceAfter=8,
        )
        meta_style = ParagraphStyle(
            "PolioMeta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "PolioHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=accent,
            spaceBefore=10,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "PolioBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=colors.black,
            spaceAfter=6,
        )
        appendix_style = ParagraphStyle(
            "PolioAppendix",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        )

        story = [
            Paragraph(context.project_title, title_style),
            Paragraph(template.label.upper(), template_style),
            Paragraph(f"Draft: {context.draft_title}", meta_style),
            Paragraph(f"Requested by: {context.requested_by or 'anonymous'}", meta_style),
            Paragraph(f"Template intent: {template.description}", meta_style),
            Spacer(1, 12),
        ]

        for section_title, lines in split_markdown_sections(context.content_markdown):
            if section_title:
                story.append(Paragraph(section_title, heading_style))
            if not lines:
                story.append(Paragraph("No content provided.", body_style))
            else:
                for line in lines:
                    text = self._escape_text(line)
                    if line.startswith("- ") or line.startswith("* "):
                        story.append(Paragraph(f"&#8226; {self._escape_text(line[2:].strip())}", body_style))
                    else:
                        story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 6))

        appendix_lines = self._build_provenance_appendix(context)
        if appendix_lines:
            story.append(Spacer(1, 12))
            story.append(Paragraph("Provenance Appendix", heading_style))
            for line in appendix_lines:
                story.append(Paragraph(self._escape_text(line), appendix_style))

        doc.build(story, onFirstPage=self._draw_footer, onLaterPages=self._draw_footer)

    @staticmethod
    def _build_provenance_appendix(context: RenderBuildContext) -> list[str]:
        template = context.resolve_template()
        policy = context.export_policy
        if not policy.include_provenance_appendix or not template.supports_provenance_appendix:
            return []

        return [
            "This appendix summarizes the evidence basis used for the export.",
            *build_provenance_appendix_lines(
                evidence_map=context.evidence_map,
                authenticity_log_lines=context.authenticity_log_lines,
                hide_internal=policy.hide_internal_provenance_on_final_export,
                max_evidence_items=5,
                max_authenticity_notes=3,
            ),
        ]

    @staticmethod
    def _draw_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 20, f"polio export - page {canvas.getPageNumber()}")
        canvas.restoreState()

    @staticmethod
    def _escape_text(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
