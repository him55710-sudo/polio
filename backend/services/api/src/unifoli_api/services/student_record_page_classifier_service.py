from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PageCategory(str, Enum):
    STUDENT_INFO = "student_info"
    ATTENDANCE = "attendance"
    AWARDS = "awards"
    LICENSES = "licenses"
    EXTRACURRICULAR = "extracurricular"
    GRADES_AND_NOTES = "grades_and_notes"
    READING = "reading"
    BEHAVIOR = "behavior"
    UNKNOWN = "unknown"


class PageClassification(BaseModel):
    page_number: int
    category: PageCategory
    confidence: float
    matched_tokens: list[str]
    is_continuation: bool = False


# Patterns for each category
CATEGORY_PATTERNS = {
    PageCategory.STUDENT_INFO: (
        "?¸ì Â·?™ì ?¬í•­",
        "?¸ì  ?™ì ?¬í•­",
        "?¸ì ?¬í•­",
        "?™ì ?¬í•­",
        "?±ëª…",
        "ì£¼ë??±ë¡ë²ˆí˜¸",
        "ì£¼ì†Œ",
    ),
    PageCategory.ATTENDANCE: (
        "ì¶œê²°?í™©",
        "ê²°ì„",
        "ì§€ê°?,
        "ì¡°í‡´",
        "ê²°ê³¼",
        "ì§ˆë³‘",
        "ë¯¸ì¸??,
    ),
    PageCategory.AWARDS: (
        "?˜ìƒê²½ë ¥",
        "?˜ìƒ ê²½ë ¥",
        "?˜ìƒëª?,
        "?±ê¸‰(??",
        "?˜ìƒ?°ì›”??,
        "?˜ì—¬ê¸°ê?",
    ),
    PageCategory.LICENSES: (
        "?ê²©ì¦?ë°??¸ì¦ ì·¨ë“?í™©",
        "?ê²©ì¦?,
        "ê¸°ìˆ ?ê²©",
        "êµ??ê¸°ìˆ ?ê²©",
    ),
    PageCategory.EXTRACURRICULAR: (
        "ì°½ì˜??ì²´í—˜?œë™",
        "ì°½ì˜?ì²´?˜í™œ??,
        "?ìœ¨?œë™",
        "?™ì•„ë¦¬í™œ??,
        "ë´‰ì‚¬?œë™",
        "ì§„ë¡œ?œë™",
        "?¹ê¸°?¬í•­",
    ),
    PageCategory.GRADES_AND_NOTES: (
        "êµê³¼?™ìŠµë°œë‹¬?í™©",
        "?¸ë??¥ë ¥ ë°??¹ê¸°?¬í•­",
        "?¸íŠ¹",
        "?ì ??,
        "ê³¼ëª©",
        "?¨ìœ„",
        "?±ì·¨??,
        "?ì°¨?±ê¸‰",
    ),
    PageCategory.READING: (
        "?…ì„œ?œë™?í™©",
        "?…ì„œ ?œë™",
        "?€??,
        "?„ì„œëª?,
    ),
    PageCategory.BEHAVIOR: (
        "?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬",
        "?‰ë™?¹ì„±",
        "ì¢…í•©?˜ê²¬",
    ),
}


class StudentRecordPageClassifierService:
    """
    Compatibility wrapper used by StudentRecordPipelineService.
    """

    def classify_pages(self, pages: list[Any]) -> list[PageClassification]:
        normalized_pages: list[dict[str, Any]] = []
        for index, page in enumerate(pages, start=1):
            if isinstance(page, dict):
                page_number = int(page.get("page_number") or index)
                text = str(page.get("text") or page.get("raw_text") or "")
                normalized_pages.append({"page_number": page_number, "text": text})
                continue
            extract_text = getattr(page, "extract_text", None)
            if callable(extract_text):
                try:
                    text = str(extract_text() or "")
                except Exception:  # noqa: BLE001
                    text = ""
                normalized_pages.append({"page_number": index, "text": text})
                continue
            normalized_pages.append({"page_number": index, "text": str(page or "")})

        return classify_pages(normalized_pages)


def classify_page(page_number: int, text: str) -> PageClassification:
    """
    Classifies a single page based on its text content.
    """
    if not text.strip():
        return PageClassification(
            page_number=page_number,
            category=PageCategory.UNKNOWN,
            confidence=0.0,
            matched_tokens=[],
        )

    hits: dict[PageCategory, list[str]] = {}
    
    for category, patterns in CATEGORY_PATTERNS.items():
        matched = []
        for pattern in patterns:
            if pattern in text:
                matched.append(pattern)
        if matched:
            hits[category] = matched

    if not hits:
        # Check for continuation patterns
        if "ê³„ì†" in text or "?´ì–´?? in text:
             return PageClassification(
                page_number=page_number,
                category=PageCategory.UNKNOWN,
                confidence=0.1,
                matched_tokens=["continuation_marker"],
                is_continuation=True
            )

        return PageClassification(
            page_number=page_number,
            category=PageCategory.UNKNOWN,
            confidence=0.0,
            matched_tokens=[],
        )

    # Sort categories by hit count (len of matched tokens)
    sorted_hits = sorted(hits.items(), key=lambda x: len(x[1]), reverse=True)
    best_category, best_tokens = sorted_hits[0]
    
    # Simple confidence score (could be more sophisticated)
    confidence = min(0.95, len(best_tokens) * 0.2 + 0.1)
    
    # Check for continuation headers like "[êµê³¼?™ìŠµë°œë‹¬?í™©(ê³„ì†)]"
    is_continuation = "ê³„ì†" in text and best_category.value in text

    return PageClassification(
        page_number=page_number,
        category=best_category,
        confidence=confidence,
        matched_tokens=best_tokens,
        is_continuation=is_continuation
    )


def classify_pages(pages: list[dict[str, Any]]) -> list[PageClassification]:
    """
    Classifies a list of pages.
    """
    classifications = []
    for page in pages:
        page_number = page.get("page_number", 0)
        text = page.get("text") or page.get("raw_text") or ""
        classifications.append(classify_page(page_number, text))
    
    # Refine classification based on context (continuation logic)
    refined = []
    prev_category = PageCategory.UNKNOWN
    
    for i, cls in enumerate(classifications):
        if cls.category == PageCategory.UNKNOWN and prev_category != PageCategory.UNKNOWN:
            # If current page is unknown but looks like it follows the previous one
            # We can tentatively mark it as continuation if there are certain signals
            # For now, we'll keep it as is and let the section parser handle grouping.
            pass
        
        refined.append(cls)
        if cls.category != PageCategory.UNKNOWN:
            prev_category = cls.category
            
    return refined
