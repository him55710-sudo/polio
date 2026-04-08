from __future__ import annotations

from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
        message = "PDF renderer completed with styled diagnosis layout."
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
            leftMargin=48,
            rightMargin=48,
            topMargin=46,
            bottomMargin=54,
            title=context.draft_title,
            author=context.requested_by or "polio backend",
        )
        sections = split_markdown_sections(context.content_markdown)
        if not sections:
            sections = [("Overview", ["No content provided."])]

        styles = getSampleStyleSheet()
        accent = colors.HexColor(template.preview.accent_color)
        title_style = ParagraphStyle(
            "PolioCoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            spaceAfter=14,
        )
        lead_style = ParagraphStyle(
            "PolioLead",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#334155"),
            spaceAfter=12,
        )
        badge_style = ParagraphStyle(
            "PolioBadge",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=accent,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
        meta_key_style = ParagraphStyle(
            "PolioMetaKey",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#0f172a"),
        )
        meta_value_style = ParagraphStyle(
            "PolioMetaValue",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
        )
        heading_style = ParagraphStyle(
            "PolioHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=24,
            textColor=accent,
            spaceBefore=4,
            spaceAfter=8,
        )
        section_intro_style = ParagraphStyle(
            "PolioSectionIntro",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "PolioBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=17,
            textColor=colors.HexColor("#111827"),
            spaceAfter=8,
        )
        bullet_style = ParagraphStyle(
            "PolioBullet",
            parent=body_style,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=6,
        )
        callout_style = ParagraphStyle(
            "PolioCallout",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_CENTER,
        )
        summary_title_style = ParagraphStyle(
            "PolioSummaryTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        summary_body_style = ParagraphStyle(
            "PolioSummaryBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
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
        story: list = []

        cover_meta_data = [
            [
                Paragraph("<b>Project</b>", meta_key_style),
                Paragraph(self._escape_text(context.project_title), meta_value_style),
            ],
            [
                Paragraph("<b>Template</b>", meta_key_style),
                Paragraph(self._escape_text(template.label), meta_value_style),
            ],
            [
                Paragraph("<b>Exported</b>", meta_key_style),
                Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), meta_value_style),
            ],
            [
                Paragraph("<b>Requested By</b>", meta_key_style),
                Paragraph(self._escape_text(context.requested_by or "anonymous"), meta_value_style),
            ],
        ]
        cover_meta_table = Table(cover_meta_data, colWidths=[doc.width * 0.24, doc.width * 0.76], hAlign="LEFT")
        cover_meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#dbeafe")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story.extend(
            [
                Paragraph("DIAGNOSIS REPORT", badge_style),
                Paragraph(self._escape_text(context.draft_title), title_style),
                Paragraph(self._escape_text(template.description), lead_style),
                cover_meta_table,
                Spacer(1, 14),
                Paragraph("This export is grounded in parsed student-record evidence and keeps auditable structure.", section_intro_style),
            ]
        )

        roadmap = [self._escape_text(title or f"Section {index + 1}") for index, (title, _lines) in enumerate(sections[:6])]
        if roadmap:
            story.append(Paragraph("Roadmap", heading_style))
            for item in roadmap:
                story.append(Paragraph(f"&#8226; {item}", bullet_style))

        story.append(PageBreak())

        highlights = self._extract_highlights(sections, max_items=8)
        story.append(Paragraph("Executive Snapshot", heading_style))
        story.append(
            Paragraph(
                "A concise view of the strongest grounded points and the next edits required before final submission.",
                lead_style,
            )
        )
        summary_cards = Table(
            [
                [
                    Paragraph("Grounded Focus", summary_title_style),
                    Paragraph("Structure", summary_title_style),
                    Paragraph("Authenticity Rule", summary_title_style),
                ],
                [
                    Paragraph(
                        self._escape_text(
                            context.draft_title or "Keep one defensible inquiry focus and avoid unsupported expansion."
                        ),
                        summary_body_style,
                    ),
                    Paragraph(
                        self._escape_text(
                            "Cover, snapshot, section-by-section evidence notes, and provenance appendix."
                        ),
                        summary_body_style,
                    ),
                    Paragraph(
                        self._escape_text(
                            "Do not claim achievements that are not present in the student record."
                        ),
                        summary_body_style,
                    ),
                ],
            ],
            colWidths=[doc.width / 3.0] * 3,
            hAlign="LEFT",
        )
        summary_cards.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbeafe")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.extend([summary_cards, Spacer(1, 14)])

        if highlights:
            story.append(Paragraph("Key Points", heading_style))
            for line in highlights:
                story.append(Paragraph(f"&#8226; {self._escape_text(line)}", bullet_style))

        for index, (section_title, lines) in enumerate(sections):
            story.append(PageBreak())
            title = self._escape_text(section_title or f"Section {index + 1}")
            story.append(Paragraph(f"Section {index + 1}", badge_style))
            story.append(Paragraph(title, heading_style))
            story.append(Paragraph("Evidence-grounded section content", section_intro_style))
            if not lines:
                story.append(Paragraph("No content provided.", body_style))
            else:
                for line in lines:
                    text = self._escape_text(line)
                    if line.startswith("- ") or line.startswith("* "):
                        story.append(Paragraph(f"&#8226; {self._escape_text(line[2:].strip())}", bullet_style))
                    else:
                        story.append(Paragraph(text, body_style))

            section_callout = Table(
                [[Paragraph("Review each claim against source evidence before final submission.", callout_style)]],
                colWidths=[doc.width],
            )
            section_callout.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.extend([Spacer(1, 8), section_callout])

        appendix_lines = self._build_provenance_appendix(context)
        if appendix_lines:
            story.append(PageBreak())
            story.append(Paragraph("Provenance Appendix", heading_style))
            for line in appendix_lines:
                story.append(Paragraph(self._escape_text(line), appendix_style))

        minimum_pages = 5
        estimated_page_count = 2 + len(sections) + (1 if appendix_lines else 0)
        supplemental_pages = max(0, minimum_pages - estimated_page_count)
        for index in range(supplemental_pages):
            story.append(PageBreak())
            story.append(Paragraph(f"Supplemental Page {index + 1}", badge_style))
            story.append(Paragraph("Revision Checklist", heading_style))
            story.append(
                Paragraph(
                    "Use this page to record final edits, evidence links, and authenticity checks before sharing the diagnosis report.",
                    body_style,
                )
            )
            story.append(Paragraph("&#8226; Confirm every key claim has a source excerpt.", bullet_style))
            story.append(Paragraph("&#8226; Keep timelines and activity scope factually grounded.", bullet_style))
            story.append(Paragraph("&#8226; Note one actionable improvement for the next draft cycle.", bullet_style))

        doc.build(
            story,
            onFirstPage=lambda canvas, doc_obj: self._draw_page_chrome(canvas, doc_obj, accent, template.label),
            onLaterPages=lambda canvas, doc_obj: self._draw_page_chrome(canvas, doc_obj, accent, template.label),
        )

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
    def _draw_page_chrome(canvas, doc, accent: colors.Color, template_label: str) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(accent)
        canvas.rect(0, height - 18, width, 18, stroke=0, fill=1)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.white)
        canvas.drawString(doc.leftMargin, height - 12, f"POLIO DIAGNOSIS REPORT | {template_label.upper()}")

        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.setLineWidth(0.6)
        canvas.line(doc.leftMargin, 34, width - doc.rightMargin, 34)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 20, "Grounded export")
        canvas.drawRightString(width - doc.rightMargin, 20, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    @staticmethod
    def _escape_text(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _extract_highlights(sections: list[tuple[str, list[str]]], *, max_items: int) -> list[str]:
        highlights: list[str] = []
        for _title, lines in sections:
            for raw in lines:
                cleaned = raw.strip()
                if not cleaned:
                    continue
                if cleaned.startswith("- "):
                    cleaned = cleaned[2:].strip()
                if cleaned.startswith("* "):
                    cleaned = cleaned[2:].strip()
                highlights.append(cleaned)
                if len(highlights) >= max_items:
                    return highlights
        return highlights
