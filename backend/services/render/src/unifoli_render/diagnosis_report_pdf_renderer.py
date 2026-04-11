from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from unifoli_render.diagnosis_report_design_contract import get_diagnosis_report_design_contract


def render_consultant_diagnosis_pdf(
    *,
    report_payload: dict[str, Any],
    output_path: Path,
    report_mode: str,
    template_id: str,
    include_appendix: bool,
    include_citations: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_name, font_bold = _resolve_font_names()

    render_hints = report_payload.get("render_hints") if isinstance(report_payload.get("render_hints"), dict) else {}
    design_contract = render_hints.get("design_contract") if isinstance(render_hints, dict) else None
    if not isinstance(design_contract, dict):
        design_contract = get_diagnosis_report_design_contract(
            report_mode=report_mode,
            template_id=template_id,
            template_section_schema=(),
        )

    margins = design_contract.get("canvas", {}).get("margins", {}) if isinstance(design_contract.get("canvas"), dict) else {}
    minimum_pages = int(
        report_payload.get("render_hints", {}).get("minimum_pages")
        or design_contract.get("canvas", {}).get("minimum_pages")
        or (10 if report_mode == "premium_10p" else 5)
    )

    sections = [item for item in report_payload.get("sections", []) if isinstance(item, dict)]
    sections = _order_sections(sections, design_contract=design_contract)
    score_blocks = [item for item in report_payload.get("score_blocks", []) if isinstance(item, dict)]
    score_groups = [item for item in report_payload.get("score_groups", []) if isinstance(item, dict)]
    roadmap = [item for item in report_payload.get("roadmap", []) if isinstance(item, dict)]
    citations = [item for item in report_payload.get("citations", []) if isinstance(item, dict)]
    uncertainty_notes = [str(item).strip() for item in report_payload.get("uncertainty_notes", []) if str(item).strip()]
    appendix_notes = [str(item).strip() for item in report_payload.get("appendix_notes", []) if str(item).strip()]
    public_appendix_enabled = bool(render_hints.get("public_appendix_enabled", include_appendix))
    public_citations_enabled = bool(render_hints.get("public_citations_enabled", include_citations))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=float(margins.get("left", 46)),
        rightMargin=float(margins.get("right", 46)),
        topMargin=float(margins.get("top", 44)),
        bottomMargin=float(margins.get("bottom", 50)),
        title=str(report_payload.get("title") or "?좊땲?대━ 吏꾨떒 蹂닿퀬??),
        author="?좊땲?대━ 吏꾨떒",
    )

    color_tokens = design_contract.get("colors", {}) if isinstance(design_contract.get("colors"), dict) else {}
    style_tokens = _build_style_tokens(
        design_contract=design_contract,
        font_name=font_name,
        font_bold=font_bold,
        color_tokens=color_tokens,
    )

    story: list[Any] = []

    # Cover page
    story.extend(
        [
            Paragraph("?좊땲?대━ 而⑥꽕?댄듃 吏꾨떒 由ы룷??, style_tokens["cover_label"]),
            Paragraph(_escape(str(report_payload.get("title") or "?좊땲?대━ 吏꾨떒 蹂닿퀬??)), style_tokens["cover_title"]),
            Paragraph(_escape(str(report_payload.get("subtitle") or "洹쇨굅 以묒떖 吏꾨떒 寃곌낵")), style_tokens["cover_subtitle"]),
            Spacer(1, style_tokens["spacing"]["cover_block_gap"]),
        ]
    )

    cover_meta_rows = [
        ["????꾨줈?앺듃", _escape(str(report_payload.get("student_target_context") or "-"))],
        ["由ы룷??紐⑤뱶", "?꾨━誘몄뾼 10履? if report_mode == "premium_10p" else "而댄뙥???붿빟"],
        ["?쒗뵆由?, "?대? ?쒖? ?쒗뵆由?],
        [
            "?듭떖 ?먯젙",
            _escape(str(render_hints.get("one_line_verdict") or "?숈깮遺 洹쇨굅 湲곕컲?쇰줈 吏꾨떒 寃곕줎???뺣━?덉뒿?덈떎.")),
        ],
        [
            "遺꾩꽍 ?좊ː??,
            f"{int(round(float(render_hints.get('analysis_confidence_score', 0.0)) * 100))}%",
        ],
        ["?앹꽦 ?쒓컖", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M ?멸퀎?쒖???)],
    ]
    cover_meta_table = Table(
        cover_meta_rows,
        colWidths=[doc.width * 0.22, doc.width * 0.78],
        hAlign="LEFT",
    )
    cover_meta_table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_hex(color_tokens.get("surface_soft"), "#F8FAFC"), _hex(color_tokens.get("surface_panel"), "#EEF2FF")]),
                ("BOX", (0, 0), (-1, -1), 0.8, _hex(color_tokens.get("line_soft"), "#D7DEE8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, _hex(color_tokens.get("line_soft"), "#D7DEE8")),
                ("FONTNAME", (0, 0), (0, -1), font_bold),
                ("FONTNAME", (1, 0), (1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), style_tokens["typography"]["meta_size"]),
                ("LEFTPADDING", (0, 0), (-1, -1), style_tokens["spacing"]["table_cell_padding"]),
                ("RIGHTPADDING", (0, 0), (-1, -1), style_tokens["spacing"]["table_cell_padding"]),
                ("TOPPADDING", (0, 0), (-1, -1), style_tokens["spacing"]["list_item_gap"] + 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), style_tokens["spacing"]["list_item_gap"] + 1),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(cover_meta_table)
    story.append(Spacer(1, style_tokens["spacing"]["cover_block_gap"]))

    story.append(
        _build_callout(
            text="吏꾨떒?쒕뒗 ?숈깮遺 洹쇨굅瑜?湲곕컲?쇰줈 ?묒꽦?섎ŉ, 遺덊솗?ㅽ븳 ??ぉ? 蹂꾨룄 寃利?硫붾え濡??덈궡?⑸땲??",
            width=doc.width,
            style=style_tokens["callout"],
            border_color=_hex(color_tokens.get("line_evidence"), "#C7D2FE"),
            fill_color=_hex(color_tokens.get("surface_evidence"), "#EEF2FF"),
            padding=style_tokens["spacing"]["card_padding"],
        )
    )

    section_groups = _resolve_section_groups(design_contract=design_contract, section_ids=[str(item.get("id") or "") for item in sections])
    section_by_id = {str(item.get("id") or ""): item for item in sections}
    section_order = [str(item.get("id") or "") for item in sections]
    section_number = {section_id: idx + 1 for idx, section_id in enumerate(section_order)}

    for group in section_groups:
        available_ids = [section_id for section_id in group if section_id in section_by_id]
        if not available_ids:
            continue
        story.append(PageBreak())
        for section_id in available_ids:
            section = section_by_id[section_id]
            heading = f"{section_number.get(section_id, 0)}. {str(section.get('title') or '吏꾨떒 ?뱀뀡')}"
            story.append(Paragraph(_escape(heading), style_tokens["h2"]))
            subtitle = str(section.get("subtitle") or "").strip()
            if subtitle:
                story.append(Paragraph(_escape(subtitle), style_tokens["subtitle"]))

            story.extend(
                _render_section_body(
                    section,
                    style_tokens["body"],
                    style_tokens["bullet"],
                    section_id=section_id,
                )
            )

            if section_id == "record_baseline_dashboard":
                story.append(Spacer(1, style_tokens["spacing"]["paragraph_gap"]))
                if score_groups:
                    for group in score_groups:
                        group_title = str(group.get("title") or "?먯닔 洹몃９")
                        story.append(Paragraph(_escape(group_title), style_tokens["h3"]))
                        group_blocks = [item for item in group.get("blocks", []) if isinstance(item, dict)]
                        if group_blocks:
                            story.append(
                                _build_score_table(
                                    score_blocks=group_blocks,
                                    doc=doc,
                                    style_tokens=style_tokens,
                                    font_name=font_name,
                                    font_bold=font_bold,
                                    color_tokens=color_tokens,
                                    compact=True,
                                )
                            )
                        note = str(group.get("note") or "").strip()
                        if note:
                            story.append(Paragraph(_escape(note), style_tokens["meta"]))
                        story.append(Spacer(1, style_tokens["spacing"]["list_item_gap"]))
                elif score_blocks:
                    story.append(Paragraph("?됯? ?먯닔", style_tokens["h3"]))
                    story.append(
                        _build_score_table(
                            score_blocks=score_blocks,
                            doc=doc,
                            style_tokens=style_tokens,
                            font_name=font_name,
                            font_bold=font_bold,
                            color_tokens=color_tokens,
                        )
                    )

            if section_id == "roadmap" and roadmap:
                story.append(Spacer(1, style_tokens["spacing"]["paragraph_gap"]))
                story.append(Paragraph("?④퀎蹂??ㅽ뻾 怨꾪쉷", style_tokens["h3"]))
                for roadmap_item in roadmap:
                    story.append(Paragraph(_escape(str(roadmap_item.get("title") or "-")), style_tokens["meta_strong"]))
                    for action in list(roadmap_item.get("actions") or [])[:4]:
                        story.append(Paragraph(f"&#8226; {_escape(str(action))}", style_tokens["bullet"]))

            evidence_items = [item for item in section.get("evidence_items", []) if isinstance(item, dict)]
            should_render_evidence = section_id in {"evidence_cards", "major_fit", "risk_analysis"}
            if evidence_items and should_render_evidence:
                story.append(Spacer(1, style_tokens["spacing"]["paragraph_gap"]))
                story.append(Paragraph("洹쇨굅 ?듭빱", style_tokens["h3"]))
                max_evidence_cards = 3 if section_id == "evidence_cards" else 2
                for evidence in evidence_items[:max_evidence_cards]:
                    source_label = str(evidence.get("source_label") or "洹쇨굅")
                    page = evidence.get("page_number")
                    excerpt = str(evidence.get("excerpt") or "").strip()
                    support_status = _support_status_label(str(evidence.get("support_status") or "verified"))
                    source_text = f"{source_label} {page}履? if page else source_label
                    text = f"{source_text} ({support_status}): {excerpt}"
                    story.append(
                        _build_callout(
                            text=text,
                            width=doc.width,
                            style=style_tokens["meta"],
                            border_color=_hex(color_tokens.get("line_evidence"), "#C7D2FE"),
                            fill_color=_hex(color_tokens.get("surface_evidence"), "#EEF2FF"),
                            padding=style_tokens["spacing"]["card_padding"],
                        )
                    )
                    story.append(Spacer(1, style_tokens["spacing"]["list_item_gap"]))

            unsupported_claims = [str(item).strip() for item in section.get("unsupported_claims", []) if str(item).strip()]
            if unsupported_claims:
                story.append(
                    _build_callout(
                        text="寃利??꾩슂: " + " | ".join(unsupported_claims[:4]),
                        width=doc.width,
                        style=style_tokens["callout"],
                        border_color=_hex(color_tokens.get("line_warning"), "#FDBA74"),
                        fill_color=_hex(color_tokens.get("surface_warning"), "#FFF7ED"),
                        padding=style_tokens["spacing"]["card_padding"],
                    )
                )

            verification_needed = [str(item).strip() for item in section.get("additional_verification_needed", []) if str(item).strip()]
            if verification_needed:
                story.append(Spacer(1, style_tokens["spacing"]["list_item_gap"]))
                story.append(Paragraph("異붽? ?뺤씤 ?꾩슂", style_tokens["meta_strong"]))
                for item in verification_needed[:2]:
                    story.append(Paragraph(f"&#8226; {_escape(item)}", style_tokens["bullet"]))

            story.append(Spacer(1, style_tokens["spacing"]["section_gap"]))

    appendix_layout = design_contract.get("appendix_layout", {}) if isinstance(design_contract.get("appendix_layout"), dict) else {}
    max_uncertainty_items = int(appendix_layout.get("max_uncertainty_items", 12))
    max_citation_items = int(appendix_layout.get("max_citation_items", 60))

    if public_appendix_enabled and (uncertainty_notes or appendix_notes):
        story.append(PageBreak())
        story.append(Paragraph("遺濡?/ 遺덊솗?ㅼ꽦 諛?寃利?硫붾え", style_tokens["h2"]))
        if uncertainty_notes:
            story.append(Paragraph("遺덊솗?ㅼ꽦 諛?寃利?寃쎄퀎", style_tokens["h3"]))
            for note in uncertainty_notes[:max_uncertainty_items]:
                story.append(Paragraph(f"&#8226; {_escape(note)}", style_tokens["bullet"]))
        if appendix_notes:
            story.append(Spacer(1, style_tokens["spacing"]["section_gap"]))
            story.append(Paragraph("?댁쁺/?뚯떛 硫붾え", style_tokens["h3"]))
            for note in appendix_notes[:max_uncertainty_items]:
                story.append(Paragraph(f"&#8226; {_escape(note)}", style_tokens["bullet"]))

    if public_citations_enabled and citations:
        story.append(PageBreak())
        story.append(Paragraph("遺濡?/ 異쒖쿂 洹쇨굅 紐⑸줉", style_tokens["h2"]))
        for citation in citations[:max_citation_items]:
            source = str(citation.get("source_label") or "異쒖쿂")
            page_number = citation.get("page_number")
            excerpt = str(citation.get("excerpt") or "").strip()
            score = citation.get("relevance_score")
            support_status = _support_status_label(str(citation.get("support_status") or "verified"))
            prefix = f"{source} ({page_number}履?" if page_number else source
            if score is not None:
                prefix = f"{prefix} | 愿?⑤룄={score} | {support_status}"
            story.append(Paragraph(f"&#8226; {_escape(prefix)}: {_escape(excerpt)}", style_tokens["bullet"]))

    estimated_pages = _estimate_pages(
        section_groups=section_groups,
        has_uncertainty=bool(public_appendix_enabled and (uncertainty_notes or appendix_notes)),
        has_citations=bool(public_citations_enabled and citations),
    )
    filler_pages = max(0, minimum_pages - estimated_pages)
    for idx in range(filler_pages):
        story.append(PageBreak())
        story.append(Paragraph(f"?덉쭏 ?먭? 硫붾え {idx + 1}", style_tokens["h2"]))
        story.append(
            Paragraph(
                "???섏씠吏??理쒖쥌 ?쒖텧 ??吏꾨떒 臾몄옣怨?洹쇨굅 ?뺥빀?깆쓣 ?먭??섍린 ?꾪븳 ?뺤씤 ?곸뿭?낅땲?? "
                "遺덊솗?ㅽ븳 ??ぉ? 諛섎뱶??'異붽? ?뺤씤 ?꾩슂'濡??쒖떆??二쇱꽭??",
                style_tokens["body"],
            )
        )
        story.append(Paragraph("&#8226; ?듭떖 二쇱옣留덈떎 異쒖쿂 ?쇱씤 1媛??댁긽 ?곌껐", style_tokens["bullet"]))
        story.append(Paragraph("&#8226; 寃利?誘몄셿猷?臾몄옣? 異붽? ?뺤씤 ?꾩슂濡??쒖떆", style_tokens["bullet"]))
        story.append(Paragraph("&#8226; 怨쇱옣쨌?덉쐞쨌洹쇨굅 遺議??쒗쁽 ?쒓굅", style_tokens["bullet"]))

    doc.build(
        story,
        onFirstPage=lambda canvas, doc_obj: _draw_page_chrome(canvas, doc_obj, template_id, font_name, font_bold, color_tokens),
        onLaterPages=lambda canvas, doc_obj: _draw_page_chrome(canvas, doc_obj, template_id, font_name, font_bold, color_tokens),
    )


def _build_style_tokens(*, design_contract: dict[str, Any], font_name: str, font_bold: str, color_tokens: dict[str, Any]) -> dict[str, Any]:
    styles = getSampleStyleSheet()
    typography = design_contract.get("typography", {}) if isinstance(design_contract.get("typography"), dict) else {}
    spacing = design_contract.get("spacing", {}) if isinstance(design_contract.get("spacing"), dict) else {}
    body_font_size = max(
        11.0,
        float(typography.get("body", {}).get("font_size", 11.0) if isinstance(typography.get("body"), dict) else 11.0),
    )
    body_leading = max(
        16.0,
        float(typography.get("body", {}).get("leading", 16.0) if isinstance(typography.get("body"), dict) else 16.0),
    )
    common_wrap = {
        "wordWrap": "CJK",
        "splitLongWords": True,
    }
    title_style = ParagraphStyle(
        "DiagnosisCoverTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=float(typography.get("cover_title", {}).get("font_size", 26) if isinstance(typography.get("cover_title"), dict) else 26),
        leading=float(typography.get("cover_title", {}).get("leading", 32) if isinstance(typography.get("cover_title"), dict) else 32),
        textColor=_hex(color_tokens.get("brand_primary"), "#1E3A5F"),
        alignment=TA_LEFT,
        spaceAfter=10,
        **common_wrap,
    )
    subtitle_style = ParagraphStyle(
        "DiagnosisCoverSubtitle",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=max(11.2, float(typography.get("cover_subtitle", {}).get("font_size", 11.2) if isinstance(typography.get("cover_subtitle"), dict) else 11.2)),
        leading=max(16.0, float(typography.get("cover_subtitle", {}).get("leading", 16.0) if isinstance(typography.get("cover_subtitle"), dict) else 16.0)),
        textColor=_hex(color_tokens.get("text_secondary"), "#334155"),
        alignment=TA_LEFT,
        spaceAfter=8,
        **common_wrap,
    )
    h2_style = ParagraphStyle(
        "DiagnosisHeading",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=max(17.0, float(typography.get("section_heading", {}).get("font_size", 17) if isinstance(typography.get("section_heading"), dict) else 17)),
        leading=max(22.0, float(typography.get("section_heading", {}).get("leading", 22) if isinstance(typography.get("section_heading"), dict) else 22)),
        textColor=_hex(color_tokens.get("brand_secondary"), "#2B4F7B"),
        spaceBefore=4,
        spaceAfter=6,
        **common_wrap,
    )
    h3_style = ParagraphStyle(
        "DiagnosisHeading3",
        parent=styles["Heading3"],
        fontName=font_bold,
        fontSize=11.8,
        leading=15.6,
        textColor=_hex(color_tokens.get("text_primary"), "#0F172A"),
        spaceAfter=4,
        **common_wrap,
    )
    body_style = ParagraphStyle(
        "DiagnosisBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=body_font_size,
        leading=body_leading,
        textColor=_hex(color_tokens.get("text_primary"), "#0F172A"),
        spaceAfter=float(spacing.get("paragraph_gap", 6)),
        **common_wrap,
    )
    bullet_style = ParagraphStyle(
        "DiagnosisBullet",
        parent=body_style,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=float(spacing.get("list_item_gap", 4)),
        **common_wrap,
    )
    meta_style = ParagraphStyle(
        "DiagnosisMeta",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=max(9.4, float(typography.get("meta", {}).get("font_size", 9.4) if isinstance(typography.get("meta"), dict) else 9.4)),
        leading=max(13.2, float(typography.get("meta", {}).get("leading", 13.2) if isinstance(typography.get("meta"), dict) else 13.2)),
        textColor=_hex(color_tokens.get("text_muted"), "#526173"),
        alignment=TA_LEFT,
        **common_wrap,
    )
    meta_strong_style = ParagraphStyle(
        "DiagnosisMetaStrong",
        parent=meta_style,
        fontName=font_bold,
        textColor=_hex(color_tokens.get("text_secondary"), "#334155"),
        **common_wrap,
    )
    callout_style = ParagraphStyle(
        "DiagnosisCallout",
        parent=styles["BodyText"],
        fontName=font_bold,
        fontSize=10.4,
        leading=14.8,
        textColor=_hex(color_tokens.get("text_primary"), "#0F172A"),
        alignment=TA_CENTER,
        **common_wrap,
    )
    cover_label_style = ParagraphStyle(
        "DiagnosisCoverLabel",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=max(9.2, float(typography.get("cover_label", {}).get("font_size", 9.2) if isinstance(typography.get("cover_label"), dict) else 9.2)),
        leading=max(12.6, float(typography.get("cover_label", {}).get("leading", 12.6) if isinstance(typography.get("cover_label"), dict) else 12.6)),
        textColor=_hex(color_tokens.get("text_muted"), "#526173"),
        alignment=TA_LEFT,
        spaceAfter=3,
        **common_wrap,
    )
    meta_size = max(9.2, float(typography.get("meta", {}).get("font_size", 9.2) if isinstance(typography.get("meta"), dict) else 9.2))
    return {
        "cover_label": cover_label_style,
        "cover_title": title_style,
        "cover_subtitle": subtitle_style,
        "h2": h2_style,
        "h3": h3_style,
        "subtitle": meta_style,
        "body": body_style,
        "bullet": bullet_style,
        "meta": meta_style,
        "meta_strong": meta_strong_style,
        "callout": callout_style,
        "typography": {
            "meta_size": meta_size,
        },
        "spacing": {
            "cover_block_gap": float(spacing.get("cover_block_gap", 10)),
            "section_gap": float(spacing.get("section_gap", 8)),
            "paragraph_gap": float(spacing.get("paragraph_gap", 6)),
            "list_item_gap": float(spacing.get("list_item_gap", 4)),
            "card_padding": float(spacing.get("card_padding", 9)),
            "table_cell_padding": float(spacing.get("table_cell_padding", 5)),
        },
    }
def _build_score_table(
    *,
    score_blocks: list[dict[str, Any]],
    doc: SimpleDocTemplate,
    style_tokens: dict[str, Any],
    font_name: str,
    font_bold: str,
    color_tokens: dict[str, Any],
    compact: bool = False,
) -> Table:
    def _to_int(value: Any) -> int | None:
        try:
            return int(value)
        except Exception:
            return None

    def _score_bar(score: int | None) -> str:
        if score is None:
            return "?곗씠???놁쓬"
        clamped = max(0, min(100, score))
        filled = int(round(clamped / 10))
        empty = 10 - filled
        return f"{'?? * filled}{'?? * empty} {clamped}"

    if compact:
        rows = [["??ぉ", "?먯닔", "洹몃옒??, "?붿빟"]]
        for block in score_blocks:
            score = _to_int(block.get("score"))
            interpretation = str(block.get("interpretation") or "").strip()
            uncertainty = str(block.get("uncertainty_note") or "").strip()
            summary = interpretation or uncertainty or "-"
            summary = _truncate_plain(summary, 56)
            rows.append(
                [
                    _escape(str(block.get("label") or block.get("key") or "-")),
                    f"{score}?? if score is not None else "-",
                    _escape(_score_bar(score)),
                    _escape(summary),
                ]
            )
        table = Table(
            rows,
            colWidths=[doc.width * 0.24, doc.width * 0.12, doc.width * 0.22, doc.width * 0.42],
            repeatRows=1,
            hAlign="LEFT",
        )
    else:
        rows = [["??ぉ", "?먯닔", "洹몃옒??, "?댁꽍", "寃利?硫붾え"]]
        for block in score_blocks:
            score = _to_int(block.get("score"))
            rows.append(
                [
                    _escape(str(block.get("label") or block.get("key") or "-")),
                    f"{score}?? if score is not None else "-",
                    _escape(_score_bar(score)),
                    _escape(_truncate_plain(str(block.get("interpretation") or "-"), 90)),
                    _escape(_truncate_plain(str(block.get("uncertainty_note") or "-"), 70)),
                ]
            )
        table = Table(
            rows,
            colWidths=[doc.width * 0.16, doc.width * 0.10, doc.width * 0.18, doc.width * 0.32, doc.width * 0.24],
            repeatRows=1,
            hAlign="LEFT",
        )
    table_font_size = max(9.2, style_tokens["typography"]["meta_size"])
    table_top_bottom_padding = style_tokens["spacing"]["list_item_gap"] + 1
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex(color_tokens.get("surface_panel"), "#F1F5F9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), _hex(color_tokens.get("text_primary"), "#0F172A")),
                ("GRID", (0, 0), (-1, -1), 0.35, _hex(color_tokens.get("line_soft"), "#D7DEE8")),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTNAME", (0, 1), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), table_font_size),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), style_tokens["spacing"]["table_cell_padding"]),
                ("RIGHTPADDING", (0, 0), (-1, -1), style_tokens["spacing"]["table_cell_padding"]),
                ("TOPPADDING", (0, 0), (-1, -1), table_top_bottom_padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), table_top_bottom_padding),
            ]
        )
    )
    return table


def _order_sections(sections: list[dict[str, Any]], *, design_contract: dict[str, Any]) -> list[dict[str, Any]]:
    hierarchy = design_contract.get("section_hierarchy") if isinstance(design_contract.get("section_hierarchy"), dict) else {}
    required_order = hierarchy.get("required_order") if isinstance(hierarchy, dict) else []
    if not isinstance(required_order, list) or not required_order:
        return sections

    section_map = {str(section.get("id") or ""): section for section in sections}
    ordered: list[dict[str, Any]] = []
    for section_id in required_order:
        section = section_map.get(str(section_id))
        if section is not None:
            ordered.append(section)
    extras = [section for section in sections if str(section.get("id") or "") not in required_order]
    return [*ordered, *extras]


def _resolve_section_groups(*, design_contract: dict[str, Any], section_ids: list[str]) -> list[list[str]]:
    hierarchy = design_contract.get("section_hierarchy") if isinstance(design_contract.get("section_hierarchy"), dict) else {}
    groups = hierarchy.get("section_groups") if isinstance(hierarchy, dict) else None
    if not isinstance(groups, list) or not groups:
        return [[section_id] for section_id in section_ids if section_id]

    normalized: list[list[str]] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        clean = [str(section_id).strip() for section_id in group if str(section_id).strip()]
        if clean:
            normalized.append(clean)
    return normalized or [[section_id] for section_id in section_ids if section_id]


def _estimate_pages(*, section_groups: list[list[str]], has_uncertainty: bool, has_citations: bool) -> int:
    pages = 1  # cover
    pages += len([group for group in section_groups if group])
    if has_uncertainty:
        pages += 1
    if has_citations:
        pages += 1
    return pages


def _resolve_font_names() -> tuple[str, str]:
    for regular, bold in (
        ("HYSMyeongJo-Medium", "HYGothic-Medium"),
        ("HeiseiMin-W3", "HeiseiKakuGo-W5"),
    ):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(regular))
            pdfmetrics.registerFont(UnicodeCIDFont(bold))
            return regular, bold
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"


def _build_callout(
    *,
    text: str,
    width: float,
    style: ParagraphStyle,
    border_color: colors.Color,
    fill_color: colors.Color,
    padding: float,
) -> Table:
    table = Table([[Paragraph(_escape(text), style)]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill_color),
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), max(4, padding - 1)),
                ("BOTTOMPADDING", (0, 0), (-1, -1), max(4, padding - 1)),
            ]
        )
    )
    return table


def _render_section_body(
    section: dict[str, Any],
    body_style: ParagraphStyle,
    bullet_style: ParagraphStyle,
    *,
    section_id: str | None = None,
) -> list[Any]:
    lines = _markdown_to_lines(str(section.get("body_markdown") or ""))
    if not lines:
        return [Paragraph("?댁슜???꾩쭅 以鍮꾨릺吏 ?딆븯?듬땲??", body_style)]
    line_caps = {
        "record_baseline_dashboard": 5,
        "evidence_cards": 7,
        "major_fit": 7,
    }
    max_lines = line_caps.get(str(section_id or "").strip(), 8)
    if len(lines) > max_lines:
        lines = [*lines[:max_lines], "- 蹂몃Ц 遺꾨웾? ?섏씠吏 媛?낆꽦???꾪빐 ?붿빟?덉뒿?덈떎."]
    rendered: list[Any] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            rendered.append(Paragraph(f"&#8226; {_escape(stripped[2:].strip())}", bullet_style))
            continue
        rendered.append(Paragraph(_escape(stripped), body_style))
    return rendered


def _truncate_plain(text: str, limit: int) -> str:
    stripped = " ".join(str(text or "").replace("\n", " ").split())
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[: max(1, limit - 1)].rstrip()}??


def _markdown_to_lines(markdown: str) -> list[str]:
    if not markdown:
        return []
    lines = [line.rstrip() for line in markdown.replace("\r\n", "\n").split("\n")]
    normalized: list[str] = []
    for line in lines:
        if line.startswith("### "):
            normalized.append(line[4:])
            continue
        if line.startswith("## "):
            normalized.append(line[3:])
            continue
        if line.startswith("# "):
            normalized.append(line[2:])
            continue
        normalized.append(line)
    return normalized


def _draw_page_chrome(
    canvas: Any,
    doc: Any,
    template_id: str,
    font_name: str,
    font_bold: str,
    color_tokens: dict[str, Any],
) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(_hex(color_tokens.get("brand_primary"), "#1E3A5F"))
    canvas.rect(0, height - 16, width, 16, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont(font_bold, 7.4)
    canvas.drawString(doc.leftMargin, height - 11, "?좊땲?대━ 吏꾨떒 蹂닿퀬??)

    canvas.setStrokeColor(_hex(color_tokens.get("line_soft"), "#D7DEE8"))
    canvas.setLineWidth(0.6)
    canvas.line(doc.leftMargin, 32, width - doc.rightMargin, 32)
    canvas.setFont(font_name, 8.3)
    canvas.setFillColor(_hex(color_tokens.get("text_muted"), "#526173"))
    canvas.drawString(doc.leftMargin, 18, "洹쇨굅 以묒떖 吏꾨떒 由ы룷??)
    canvas.drawRightString(width - doc.rightMargin, 18, f"{canvas.getPageNumber()} ?섏씠吏")
    canvas.restoreState()


def _support_status_label(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "verified": "寃利앸맖",
        "supported": "洹쇨굅 異⑸텇",
        "probable": "媛?μ꽦 ?믪쓬",
        "partial": "遺遺?寃利?,
        "needs_review": "寃???꾩슂",
        "needs_verification": "寃利??꾩슂",
        "unsupported": "洹쇨굅 遺議?,
    }
    return mapping.get(normalized, "?뺤씤 ?꾩슂")


def _hex(value: Any, fallback: str) -> colors.Color:
    candidate = str(value or "").strip() or fallback
    try:
        return colors.HexColor(candidate)
    except Exception:
        return colors.HexColor(fallback)


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

