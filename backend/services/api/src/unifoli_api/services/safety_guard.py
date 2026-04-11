# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from unifoli_api.services.quality_control import (
    get_quality_profile,
    normalize_quality_level,
    serialize_quality_level_info,
)
from unifoli_domain.enums import QualityLevel


class SafetyFlag(str, Enum):
    LEVEL_OVERFLOW = "level_overflow"
    FEASIBILITY_RISK = "feasibility_risk"
    FABRICATION_RISK = "fabrication_risk"
    AI_SMELL_HIGH = "ai_smell_high"
    REFERENCE_UNSUPPORTED = "reference_unsupported"
    GHOSTWRITING_RISK = "ghostwriting_risk"


@dataclass(frozen=True)
class SafetyDimension:
    key: str
    label: str
    score: int
    status: str
    detail: str
    matched_count: int = 0
    unsupported_count: int = 0


@dataclass
class SafetyCheckResult:
    safety_score: int
    flags: dict[str, str]
    recommended_level: str
    downgraded: bool = False
    summary: str = ""
    checks: dict[str, SafetyDimension] = field(default_factory=dict)


_ADVANCED_TERMS = [
    r"?¸ë?ë¶?,
    r"?‘ì??•™",
    r"ë¦¬ë§Œ",
    r"?¼ê·¸?‘ì???,
    r"ë² ì´ì§€??,
    r"?•ë¥ ë¶„í¬",
    r"ë¯¸ë¶„ë°©ì •??,
    r"? ê²½ë§?,
    r"ë¨¸ì‹ ?¬ë‹ ëª¨ë¸",
    r"SCI",
    r"?¼ë¬¸ ê²Œì¬",
    r"?™íšŒ ë°œí‘œ",
]

_FEASIBILITY_PATTERNS = [
    r"?€ê·œëª¨ ?¤ë¬¸",
    r"?˜ë°± ëª?,
    r"?€???°êµ¬??,
    r"?¥ê¸° ì¶”ì ",
    r"ì§ì ‘ ?œì‘?ˆë‹¤",
    r"ì§ì ‘ ?¤í—˜??ì§„í–‰?ˆë‹¤",
    r"?¤í—˜êµ?,
    r"?€ì¡°êµ°",
    r"?„ì¥ ?¸í„°ë·?,
    r"?„ë¬¸ ?¥ë¹„",
]

_EXPERIENCE_PATTERNS = [
    r"ì§ì ‘ ?¤í—˜",
    r"?¤í—˜??ì§„í–‰",
    r"?¤í—˜???˜í–‰",
    r"?¸í„°ë·°ë? ì§„í–‰",
    r"?¤ë¬¸??ì§„í–‰",
    r"ì¸¡ì •?ˆë‹¤",
    r"ì§ì ‘ ?œì‘",
    r"?°ì´?°ë? ?˜ì§‘",
    r"?„ì¥??ë°©ë¬¸",
    r"?¼ë¬¸???½ê³  ë¶„ì„",
]

_AI_SMELL_PATTERNS = [
    r"?¹íˆ ì£¼ëª©??ë§Œí•œ ?ì?",
    r"ì¢…í•©?ìœ¼ë¡??´í´ë³´ë©´",
    r"?´ëŸ¬??ë§¥ë½?ì„œ",
    r"?œí¸?¼ë¡œ??,
    r"?œì‚¬?˜ëŠ” ë°”ê? ?¬ë‹¤",
    r"?˜ë? ?ˆëŠ” ?¸ì‚¬?´íŠ¸",
    r"?•ì¥ ê°€?¥ì„±??ë³´ì—¬ì¤€??,
    r"?¤ì¸µ?ìœ¼ë¡?ë¶„ì„",
]

_REFERENCE_PATTERNS = [
    r"?°êµ¬???°ë¥´ë©?,
    r"?¼ë¬¸",
    r"?€??,
    r"ì¶œì²˜",
    r"ì°¸ê³ ë¬¸í—Œ",
    r"? í–‰?°êµ¬",
]

_NUMERIC_PATTERN = re.compile(r"p\s*[<=>]\s*0\.\d+|\d+(?:\.\d+)?%|\d+(?:\.\d+)?ëª?\d+(?:\.\d+)???)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _collect_matches(text: str, patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(match.group(0) for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return matches


def _dimension_status(score: int) -> str:
    if score >= 80:
        return "ok"
    if score >= 60:
        return "warning"
    return "critical"


def _build_dimension(
    *,
    key: str,
    label: str,
    score: int,
    detail: str,
    matched_count: int = 0,
    unsupported_count: int = 0,
) -> SafetyDimension:
    return SafetyDimension(
        key=key,
        label=label,
        score=max(0, min(score, 100)),
        status=_dimension_status(score),
        detail=detail,
        matched_count=matched_count,
        unsupported_count=unsupported_count,
    )


def _unsupported_terms(text: str, context_text: str, patterns: list[str]) -> list[str]:
    normalized_context = _normalize_text(context_text)
    hits = _collect_matches(text, patterns)
    return [hit for hit in hits if _normalize_text(hit) not in normalized_context]


def _unsupported_numeric_claims(text: str, context_text: str) -> list[str]:
    report_tokens = {token.group(0).lower() for token in _NUMERIC_PATTERN.finditer(text)}
    context_tokens = {token.group(0).lower() for token in _NUMERIC_PATTERN.finditer(context_text)}
    return sorted(report_tokens - context_tokens)


def run_safety_check(
    report_markdown: str,
    teacher_summary: str,
    requested_level: str,
    turn_count: int,
    reference_count: int,
    turns_text: str = "",
    references_text: str = "",
) -> SafetyCheckResult:
    requested_level = normalize_quality_level(requested_level)
    profile = get_quality_profile(requested_level)

    full_text = "\n".join(part for part in [report_markdown, teacher_summary] if part).strip()
    grounding_text = "\n".join(part for part in [turns_text, references_text] if part).strip()

    flags: dict[str, str] = {}
    checks: dict[str, SafetyDimension] = {}

    advanced_hits = _collect_matches(full_text, _ADVANCED_TERMS)
    unsupported_advanced_hits = _unsupported_terms(full_text, grounding_text, _ADVANCED_TERMS)
    level_score = 100
    if requested_level == QualityLevel.LOW.value:
        level_score -= len(advanced_hits) * 22
    elif requested_level == QualityLevel.MID.value:
        level_score -= max(0, len(advanced_hits) - 1) * 18
    else:
        level_score -= max(0, len(unsupported_advanced_hits) - 1) * 14
    if turn_count < profile.minimum_turn_count:
        level_score -= (profile.minimum_turn_count - turn_count) * 8
    level_detail = (
        "?™ìƒ ?˜ì???ë§ëŠ” ?œí˜„??? ì??˜ì—ˆ?µë‹ˆ??"
        if level_score >= 80
        else f"?¬í™” ?œí˜„ {len(advanced_hits)}ê±´ì´ ê°ì??˜ì—ˆê³? ?™ìƒ ë§¥ë½?¼ë¡œ ?•ì¸?˜ì? ?Šì? ??ª©??{len(unsupported_advanced_hits)}ê±??ˆìŠµ?ˆë‹¤."
    )
    checks["student_fit"] = _build_dimension(
        key=SafetyFlag.LEVEL_OVERFLOW.value,
        label="?™ìƒ ?˜ì? ?í•©??,
        score=level_score,
        detail=level_detail,
        matched_count=len(advanced_hits),
        unsupported_count=len(unsupported_advanced_hits),
    )
    if checks["student_fit"].status != "ok":
        flags[SafetyFlag.LEVEL_OVERFLOW.value] = level_detail

    feasibility_hits = _unsupported_terms(full_text, grounding_text, _FEASIBILITY_PATTERNS)
    feasibility_score = 100 - len(feasibility_hits) * 18
    if turn_count < profile.minimum_turn_count:
        feasibility_score -= (profile.minimum_turn_count - turn_count) * 10
    feasibility_detail = (
        "?™ìƒ???¤ì œë¡??˜í–‰ ê°€?¥í•œ ë²”ìœ„ë¡?ë³´ì…?ˆë‹¤."
        if feasibility_score >= 80
        else f"?˜í–‰ ?œë„ê°€ ?’ì? ?œë™ ?œí˜„ {len(feasibility_hits)}ê±??ëŠ” ë§¥ë½ ë¶€ì¡±ì´ ê°ì??˜ì—ˆ?µë‹ˆ??"
    )
    checks["feasibility"] = _build_dimension(
        key=SafetyFlag.FEASIBILITY_RISK.value,
        label="?˜í–‰ ê°€?¥ì„±",
        score=feasibility_score,
        detail=feasibility_detail,
        matched_count=len(feasibility_hits),
        unsupported_count=len(feasibility_hits),
    )
    if checks["feasibility"].status != "ok":
        flags[SafetyFlag.FEASIBILITY_RISK.value] = feasibility_detail

    unsupported_experience_hits = _unsupported_terms(full_text, grounding_text, _EXPERIENCE_PATTERNS)
    unsupported_numeric = _unsupported_numeric_claims(full_text, grounding_text)
    fabrication_score = 100 - len(unsupported_experience_hits) * 22 - len(unsupported_numeric) * 12
    fabrication_detail = (
        "?ˆìœ„ ê²½í—˜?´ë‚˜ ê³¼ì¥???˜ì¹˜ê°€ ?•ì¸?˜ì? ?Šì•˜?µë‹ˆ??"
        if fabrication_score >= 80
        else (
            f"ê·¼ê±°ê°€ ?•ì¸?˜ì? ?Šì? ê²½í—˜ ?œìˆ  {len(unsupported_experience_hits)}ê±? "
            f"ë§¥ë½???†ëŠ” ?˜ì¹˜ ?œí˜„ {len(unsupported_numeric)}ê±´ì´ ê°ì??˜ì—ˆ?µë‹ˆ??"
        )
    )
    checks["fabrication"] = _build_dimension(
        key=SafetyFlag.FABRICATION_RISK.value,
        label="?ˆìœ„/ê³¼ì¥ ?„í—˜",
        score=fabrication_score,
        detail=fabrication_detail,
        matched_count=len(unsupported_experience_hits) + len(unsupported_numeric),
        unsupported_count=len(unsupported_experience_hits) + len(unsupported_numeric),
    )
    if checks["fabrication"].status != "ok":
        flags[SafetyFlag.FABRICATION_RISK.value] = fabrication_detail

    ai_hits = _collect_matches(full_text, _AI_SMELL_PATTERNS)
    ai_score = 100 - len(ai_hits) * 12
    ai_detail = (
        "?™ìƒ ë§íˆ¬?€ ê°€ê¹Œìš´ ?œí˜„?…ë‹ˆ??"
        if ai_score >= 80
        else f"ë²”ìš©?ì´ê³?AI ?„ìƒˆê°€ ?˜ëŠ” ë¬¸êµ¬ {len(ai_hits)}ê±´ì´ ê°ì??˜ì—ˆ?µë‹ˆ??"
    )
    checks["style"] = _build_dimension(
        key=SafetyFlag.AI_SMELL_HIGH.value,
        label="AI ?„ìƒˆ ê³¼ë‹¤ ?¬ë?",
        score=ai_score,
        detail=ai_detail,
        matched_count=len(ai_hits),
        unsupported_count=0,
    )
    if checks["style"].status != "ok":
        flags[SafetyFlag.AI_SMELL_HIGH.value] = ai_detail

    reference_mentions = _collect_matches(full_text, _REFERENCE_PATTERNS)
    reference_score = 100
    if reference_count < profile.minimum_reference_count:
        reference_score -= (profile.minimum_reference_count - reference_count) * 30
    if reference_mentions and reference_count == 0:
        reference_score -= 20
    reference_detail = (
        "ì°¸ê³ ?ë£Œ ?¬ìš© ê°•ë„ê°€ ?„ì¬ ?˜ì???ë§ìŠµ?ˆë‹¤."
        if reference_score >= 80
        else (
            f"?„ì¬ ?˜ì??€ ìµœì†Œ {profile.minimum_reference_count}ê°œì˜ ì°¸ê³ ?ë£Œë¥??”êµ¬?˜ê±°?? "
            "ì¶œì²˜ ?œí˜„??ë¹„í•´ ?¤ì œ ì°¸ê³ ?ë£Œê°€ ë¶€ì¡±í•©?ˆë‹¤."
        )
    )
    checks["references"] = _build_dimension(
        key=SafetyFlag.REFERENCE_UNSUPPORTED.value,
        label="ì°¸ê³ ?ë£Œ ì§€ì§€ ?¬ë?",
        score=reference_score,
        detail=reference_detail,
        matched_count=len(reference_mentions),
        unsupported_count=max(profile.minimum_reference_count - reference_count, 0),
    )
    if checks["references"].status != "ok":
        flags[SafetyFlag.REFERENCE_UNSUPPORTED.value] = reference_detail

    # Ghostwriting Prevention: Input Grounding Ratio
    input_char_count = len(grounding_text)
    output_char_count = len(full_text)
    expansion_ratio = output_char_count / max(input_char_count, 100)  # Min 100 chars
    
    ghostwriting_score = 100
    if expansion_ratio > 8 and output_char_count > 400:
        ghostwriting_score -= round((expansion_ratio - 8) * 12)
    
    ghostwriting_detail = (
        "?™ìƒ ë§¥ë½??ê¸°ë°˜???ì ˆ??ë¶„ëŸ‰??ê²°ê³¼?…ë‹ˆ??"
        if ghostwriting_score >= 80
        else f"?™ìƒ???œê³µ???¨ì„œ({input_char_count}????ë¹„í•´ AIê°€ ?ì„±???´ìš©({output_char_count}????ì§€?˜ì¹˜ê²?ë§ì•„ ?€???„í—˜???ˆìŠµ?ˆë‹¤."
    )
    checks["ownership"] = _build_dimension(
        key=SafetyFlag.GHOSTWRITING_RISK.value,
        label="?€??ë°?ì£¼ì²´???„í—˜",
        score=ghostwriting_score,
        detail=ghostwriting_detail,
        matched_count=round(expansion_ratio),
        unsupported_count=max(0, output_char_count - (input_char_count * 8)),
    )
    if checks["ownership"].status != "ok":
        flags[SafetyFlag.GHOSTWRITING_RISK.value] = ghostwriting_detail

    safety_score = round(
        sum(
            [
                checks["student_fit"].score,
                checks["feasibility"].score,
                checks["fabrication"].score,
                checks["style"].score,
                checks["references"].score,
                checks["ownership"].score,
            ]
        )
        / 6
    )

    recommended_level = requested_level
    if checks["fabrication"].status == "critical" or safety_score < 45:
        recommended_level = QualityLevel.LOW.value
    elif requested_level == QualityLevel.HIGH.value and (
        checks["student_fit"].status != "ok"
        or checks["feasibility"].status != "ok"
        or checks["references"].status != "ok"
        or safety_score < 70
    ):
        recommended_level = QualityLevel.MID.value
    elif requested_level == QualityLevel.MID.value and (
        checks["student_fit"].status == "critical"
        or checks["fabrication"].status != "ok"
        or safety_score < 60
    ):
        recommended_level = QualityLevel.LOW.value

    downgraded = recommended_level != requested_level
    recommended_profile = get_quality_profile(recommended_level)

    if not flags:
        summary = (
            f"?™ìƒ ?˜ì?ê³??¤ì œ ë§¥ë½??ë§ëŠ” {recommended_profile.label} ê²°ê³¼?…ë‹ˆ?? "
            "?ˆìœ„ ê²½í—˜?´ë‚˜ ê³¼ì¥ ?„í—˜???¬ê²Œ ë³´ì´ì§€ ?ŠìŠµ?ˆë‹¤."
        )
    else:
        summary = (
            f"?ˆì „???ê??ì„œ {len(flags)}ê°œì˜ ì£¼ì˜ ??ª©??ê°ì??˜ì—ˆ?µë‹ˆ?? "
            f"ìµœì¢… ?ìš© ?˜ì??€ {recommended_profile.label}?…ë‹ˆ??"
        )

    return SafetyCheckResult(
        safety_score=safety_score,
        flags=flags,
        recommended_level=recommended_level,
        downgraded=downgraded,
        summary=summary,
        checks=checks,
    )


QUALITY_LEVEL_META = {
    level: serialize_quality_level_info(get_quality_profile(level))
    for level in [QualityLevel.LOW.value, QualityLevel.MID.value, QualityLevel.HIGH.value]
}


def get_quality_meta(level: str | None) -> dict[str, object]:
    return QUALITY_LEVEL_META[normalize_quality_level(level)]
