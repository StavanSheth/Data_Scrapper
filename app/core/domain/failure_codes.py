"""Deterministic failure taxonomy for scraping runs and extraction pipeline."""

from enum import Enum
from typing import NamedTuple, Optional

class FailureCode(str, Enum):
    BROWSER_START_FAILED = "BROWSER_START_FAILED"
    NAVIGATION_FAILED = "NAVIGATION_FAILED"
    CONSENT_FAILED = "CONSENT_FAILED"
    FEED_NOT_FOUND = "FEED_NOT_FOUND"
    CARD_PARSE_FAILED = "CARD_PARSE_FAILED"
    FIELD_EXTRACTION_FAILED = "FIELD_EXTRACTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DATABASE_WRITE_FAILED = "DATABASE_WRITE_FAILED"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    CANCELLED_BY_USER = "CANCELLED_BY_USER"
    RUN_INTERRUPTED = "RUN_INTERRUPTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class FailureDetail(NamedTuple):
    code: FailureCode
    message: str
    stage: str
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "failure_code": self.code.value,
            "failure_message": self.message,
            "stage": self.stage,
            "details": self.details or {},
        }
