from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from unifoli_api.schemas.workshop import (
    WorkshopDraftPatchProposal,
    WorkshopMode,
    WorkshopStructuredDraftState,
)

DEFAULT_BLOCK_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("title", "?œëª©"),
    ("introduction_background", "?„ìž… / ë°°ê²½"),
    ("body_section_1", "ë³¸ë¡  1"),
    ("body_section_2", "ë³¸ë¡  2"),
    ("body_section_3", "ë³¸ë¡  3"),
    ("conclusion_reflection_next_step", "ê²°ë¡  / ?±ì°° / ?¤ìŒ ?¨ê³„"),
)

_PATCH_PATTERN = re.compile(r"\[DRAFT_PATCH\]([\s\S]*?)\[/DRAFT_PATCH\]", re.IGNORECASE)


def build_default_structured_draft(
    *,
    mode: WorkshopMode = "planning",
    source: str = "derived",
) -> WorkshopStructuredDraftState:
    return WorkshopStructuredDraftState(
        mode=mode,
        source="structured" if source == "structured" else "derived",
        blocks=[
            {
                "block_id": block_id,
                "heading": heading,
                "content_markdown": "",
                "attribution": "student-authored",
                "updated_at": None,
            }
            for block_id, heading in DEFAULT_BLOCK_DEFINITIONS
        ],
    )


def extract_structured_draft_from_evidence_map(
    evidence_map: dict[str, Any] | None,
) -> WorkshopStructuredDraftState | None:
    if not isinstance(evidence_map, dict):
        return None
    coauthoring = evidence_map.get("coauthoring")
    if not isinstance(coauthoring, dict):
        return None
    raw = coauthoring.get("structured_draft")
    if not isinstance(raw, dict):
        return None
    try:
        return WorkshopStructuredDraftState.model_validate(raw)
    except ValidationError:
        return None


def merge_structured_draft_into_evidence_map(
    *,
    evidence_map: dict[str, Any] | None,
    structured_draft: WorkshopStructuredDraftState,
) -> dict[str, Any]:
    merged = dict(evidence_map or {})
    coauthoring = dict(merged.get("coauthoring") or {})
    coauthoring["structured_draft"] = structured_draft.model_dump(mode="json")
    coauthoring["updated_at"] = datetime.now(timezone.utc).isoformat()
    merged["coauthoring"] = coauthoring
    return merged


def build_coauthoring_system_context(
    *,
    mode: WorkshopMode,
    structured_draft: WorkshopStructuredDraftState | None,
) -> str:
    if structured_draft is None:
        structured_draft = build_default_structured_draft(mode=mode, source="derived")
    lines = [
        "[?Œí¬??ê³µë™?‘ì„± ëª¨ë“œ]",
        f"- ?„ìž¬ ëª¨ë“œ: {mode}",
        "- ê¸°ë³¸ ?¹ì…˜ êµ¬ì¡°: title, introduction/background, body1, body2, body3, conclusion/reflection/next step",
        "- ?¹ì…˜ ?œì•ˆ?????ŒëŠ” ë³¸ë¬¸ ?¤ëª… ?¤ì— [DRAFT_PATCH] JSON [/DRAFT_PATCH] ë¸”ë¡??ì¶”ê??????ˆìŠµ?ˆë‹¤.",
        "- DRAFT_PATCH JSON ?•ì‹:",
        (
            '  {"mode":"section_drafting","block_id":"body_section_1","heading":"? íƒ","content_markdown":"ë³¸ë¬¸",'
            '"rationale":"?????¹ì…˜?¸ì?","evidence_boundary_note":"ê·¼ê±° ê²½ê³„","requires_approval":true}'
        ),
        "- ?¹ì¸ ?„ì—???™ìƒ ?‘ì„± ?´ìš©????–´?°ì? ë§ê³  ?œì•ˆ?¼ë¡œ ? ì??˜ì„¸??",
        "- ?™ìƒ ?œë™/?±ê³¼ë¥?ì¶”ì • ?ì„±?˜ì? ë§ˆì„¸??",
        "",
        "[?„ìž¬ êµ¬ì¡°??ì´ˆì•ˆ ?íƒœ]",
    ]
    for block in structured_draft.blocks:
        preview = (block.content_markdown or "").strip().replace("\n", " ")
        if len(preview) > 100:
            preview = f"{preview[:100].rstrip()}..."
        lines.append(f"- {block.block_id} | {block.heading} | {block.attribution} | {preview or '(empty)'}")
    return "\n".join(lines)


def extract_draft_patch_from_response(raw_response: str) -> tuple[str, WorkshopDraftPatchProposal | None]:
    if not raw_response:
        return "", None
    matches = _PATCH_PATTERN.findall(raw_response)
    cleaned = _PATCH_PATTERN.sub("", raw_response).strip()
    if not matches:
        return cleaned, None
    for candidate in reversed(matches):
        payload = candidate.strip()
        if payload.startswith("```"):
            payload = payload.strip("`")
            payload = payload.replace("json", "", 1).strip()
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        try:
            patch = WorkshopDraftPatchProposal.model_validate(decoded)
        except ValidationError:
            continue
        return cleaned, patch
    return cleaned, None

