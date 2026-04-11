# -*- coding: latin-1 -*-
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
    ("title", "??목"),
    ("introduction_background", "??입 / 배경"),
    ("body_section_1", "본론 1"),
    ("body_section_2", "본론 2"),
    ("body_section_3", "본론 3"),
    ("conclusion_reflection_next_step", "결론 / ??찰 / ??음 ??계"),
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
        "[??크??공동??성 모드]",
        f"- ??재 모드: {mode}",
        "- 기본 ??션 구조: title, introduction/background, body1, body2, body3, conclusion/reflection/next step",
        "- ??션 ??안??????는 본문 ??명 ??에 [DRAFT_PATCH] JSON [/DRAFT_PATCH] 블록??추????????습??다.",
        "- DRAFT_PATCH JSON ??식:",
        (
            '  {"mode":"section_drafting","block_id":"body_section_1","heading":"??택","content_markdown":"본문",'
            '"rationale":"??????션????","evidence_boundary_note":"근거 경계","requires_approval":true}'
        ),
        "- ??인 ??에????생 ??성 ??용?????????? 말고 ??안??로 ??????세??",
        "- ??생 ??동/??과???추정 ??성???? 마세??",
        "",
        "[??재 구조??초안 ??태]",
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

