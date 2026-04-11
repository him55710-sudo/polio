from enum import Enum
from typing import Optional, Any, Dict

class UniFoliErrorCode(str, Enum):
    AUTH_MISSING = "AUTH_MISSING"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PARSE_TIMEOUT = "PARSE_TIMEOUT"
    NO_USABLE_TEXT = "NO_USABLE_TEXT"
    PIPELINE_PARTIAL_FAILURE = "PIPELINE_PARTIAL_FAILURE"
    DIAGNOSIS_RUN_FAILURE = "DIAGNOSIS_RUN_FAILURE"
    REPORT_GEN_FAILURE = "REPORT_GEN_FAILURE"
    UNAUTHORIZED_GUEST = "UNAUTHORIZED_GUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class UniFoliError(Exception):
    def __init__(
        self, 
        code: UniFoliErrorCode, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
