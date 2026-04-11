from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


class RedactionReport(TypedDict):
    hard_redactions: List[str]
    generalizations: List[str]
    kept_sections: List[str]


class RedactionResponse(TypedDict):
    redacted_text: str
    redaction_report: RedactionReport
    review_flags: List[str]


@dataclass
class RedactorConfig:
    academic_year_start_month: int = 3
    first_semester_end_month: int = 8
    mask_char: str = "*"


class StudentLifeRecordRedactor:
    """Redacts high-risk personal identifiers from Korean student record text."""

    def __init__(self, config: Optional[RedactorConfig] = None):
        self.config = config or RedactorConfig()
        self._init_patterns()

    def _init_patterns(self) -> None:
        self.HARD_PATTERNS = {
            "rrn": re.compile(r"\b\d{6}-?\d{7}\b"),
            "rrn_masked": re.compile(r"\b\d{6}-\*{6,7}\b"),
            "phone": re.compile(r"\b0\d{1,2}-\d{3,4}-\d{4}\b"),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "doc_num": re.compile(r"(?:문서확인번호|발급번호|졸업대장번호)\s*[:：]?\s*([A-Za-z0-9-]+)"),
            "address": re.compile(r"(?:주소|거주지)\s*[:：]?\s*([^\n\r]+)"),
            "student_label": re.compile(r"(?:학생명|성명|이름)\s*[:：]?\s*([가-힣]{2,5})"),
            "staff_label": re.compile(
                r"(?:담임|교장|교감|행정실장|담당교사)\s*(?:성명|이름)?\s*[:：]?\s*([가-힣]{2,5})"
            ),
        }

        self.GEN_PATTERNS = {
            "high_school": re.compile(r"[가-힣]{2,12}(?:고등학교|공고|외고|예고|과학고)\b"),
            "middle_school": re.compile(r"[가-힣]{2,12}중학교\b"),
            "class_info": re.compile(r"(\d+)\s*(?:학년|학기|반|번)\s*(\d+)?"),
            "date": re.compile(r"\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b"),
            "local_inst": re.compile(r"[가-힣]{2,8}(?:교육청|도서관|센터|지원청|박물관)\b"),
        }

        self.FOOTER_PATTERN = re.compile(
            r"^(?:[가-힣A-Za-z0-9 ]+고등학교\s+\d{4}\.\d{2}\.\d{2}\s+\d+\s*/\s*\d+.*|.*\d+\s*/\s*\d+\s*페이지.*)$",
            re.MULTILINE,
        )

    def redact(self, text: str, layout_blocks: Optional[List[Dict[str, Any]]] = None) -> RedactionResponse:
        if not text:
            return {
                "redacted_text": "",
                "redaction_report": {"hard_redactions": [], "generalizations": [], "kept_sections": []},
                "review_flags": [],
            }

        report: RedactionReport = {"hard_redactions": [], "generalizations": [], "kept_sections": []}
        review_flags: List[str] = []
        working_text = text

        working_text = self._scrub_layout_patterns(working_text, report)
        working_text = self._apply_hard_redactions(working_text, report, review_flags)
        working_text = self._apply_generalizations(working_text, report)
        self._check_integrity(working_text, review_flags)

        report["kept_sections"] = [
            "세부능력 및 특기사항",
            "창의적 체험활동",
            "인적사항",
            "행동특성 및 종합의견",
        ]

        return {
            "redacted_text": working_text,
            "redaction_report": report,
            "review_flags": sorted(set(review_flags)),
        }

    def _scrub_layout_patterns(self, text: str, report: RedactionReport) -> str:
        lines = text.splitlines()
        filtered_lines = [line for line in lines if not self.FOOTER_PATTERN.match(line.strip())]
        if len(filtered_lines) < len(lines):
            report["hard_redactions"].append("Repetitive Layout Header/Footer")
        return "\n".join(filtered_lines)

    def _apply_hard_redactions(self, text: str, report: RedactionReport, flags: List[str]) -> str:
        del flags
        redacted = text

        replacements = {
            "rrn": "[주민등록번호]",
            "rrn_masked": "[주민등록번호]",
            "phone": "[PHONE_MASKED]",
            "email": "[EMAIL_MASKED]",
            "doc_num": "[문서 식별 번호]",
            "address": "[상세 주소]",
        }
        for key, replacement in replacements.items():
            redacted, count = self.HARD_PATTERNS[key].subn(replacement, redacted)
            if count:
                report["hard_redactions"].append(f"{key} ({count})")

        def _replace_student_name(match: re.Match[str]) -> str:
            return match.group(0).replace(match.group(1), "[학생명]")

        def _replace_staff_name(match: re.Match[str]) -> str:
            return match.group(0).replace(match.group(1), "[교직원명]")

        redacted, count = self.HARD_PATTERNS["student_label"].subn(_replace_student_name, redacted)
        if count:
            report["hard_redactions"].append(f"student_label ({count})")

        redacted, count = self.HARD_PATTERNS["staff_label"].subn(_replace_staff_name, redacted)
        if count:
            report["hard_redactions"].append(f"staff_label ({count})")

        return redacted

    def _apply_generalizations(self, text: str, report: RedactionReport) -> str:
        generalized = text

        generalized, count_high = self.GEN_PATTERNS["high_school"].subn("[고등학교]", generalized)
        generalized, count_mid = self.GEN_PATTERNS["middle_school"].subn("[중학교]", generalized)
        if count_high or count_mid:
            report["generalizations"].append("School Names")

        generalized, count = self.GEN_PATTERNS["local_inst"].subn("[지역기관]", generalized)
        if count:
            report["generalizations"].append(f"Local Institutions ({count})")

        generalized, count = self.GEN_PATTERNS["class_info"].subn("[학급정보]", generalized)
        if count:
            report["generalizations"].append(f"Class Details ({count})")

        def date_repl(match: re.Match[str]) -> str:
            year, month, _day = match.groups()
            year_int = int(year)
            month_int = int(month)
            if self.config.academic_year_start_month <= month_int <= self.config.first_semester_end_month:
                return f"{year_int}학년도 1학기"
            target_year = year_int if month_int >= self.config.academic_year_start_month else year_int - 1
            return f"{target_year}학년도 2학기"

        generalized, count = self.GEN_PATTERNS["date"].subn(date_repl, generalized)
        if count:
            report["generalizations"].append(f"Date Normalization ({count})")

        return generalized

    def _check_integrity(self, text: str, flags: List[str]) -> None:
        if re.search(r"\d{6}-?\d{7}", text):
            flags.append("RESIDUAL_SSN_DETECTED")
        if len(text) < 100 and len(text) > 0:
            flags.append("OVER_REDACTION_WARNING")

    def mock_image_masking(self, image_data: Any) -> Dict[str, Any]:
        del image_data
        return {
            "detections": [
                {"type": "student_photo", "action": "blur", "confidence": 0.99},
                {"type": "seal", "action": "mask", "confidence": 0.98},
                {"type": "qr_code", "action": "mask", "confidence": 1.0},
            ],
            "status": "redacted",
        }


@dataclass(slots=True)
class MaskingResult:
    text: str
    method: str = "student_record_redactor_v2"
    replacements: int = 0
    applied_presidio: bool = False
    applied_regex: bool = True
    pattern_hits: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class MaskingPipeline:
    """Wrapper kept for compatibility with ingest and diagnosis services."""

    def __init__(self, config: Optional[RedactorConfig] = None):
        self.redactor = StudentLifeRecordRedactor(config)

    def apply_masking(self, text: str) -> str:
        result = self.redactor.redact(text)
        return result["redacted_text"]

    def mask_text(self, text: str) -> MaskingResult:
        result = self.redactor.redact(text)
        report = result["redaction_report"]

        pattern_hits: Dict[str, int] = {}
        total_replacements = 0
        for item in report["hard_redactions"] + report["generalizations"]:
            match = re.search(r"\((\d+)\)$", item)
            count = int(match.group(1)) if match else 1
            key = re.sub(r"\s*\(\d+\)$", "", item).strip() or item
            pattern_hits[key] = pattern_hits.get(key, 0) + count
            total_replacements += count

        return MaskingResult(
            text=result["redacted_text"],
            replacements=total_replacements,
            pattern_hits=pattern_hits,
            warnings=result["review_flags"],
        )


def process_student_record(ocr_text: str) -> RedactionResponse:
    redactor = StudentLifeRecordRedactor()
    return redactor.redact(ocr_text)
