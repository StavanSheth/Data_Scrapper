"""Domain enums for Business Intelligence Scraper."""

from enum import Enum

class RunStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class SourceType(str, Enum):
    GOOGLE = "GOOGLE"
    PLATFORM = "PLATFORM"
    WEBSITE = "WEBSITE"

class ExtractionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    SKIPPED = "SKIPPED"

class FieldStatus(str, Enum):
    FOUND = "FOUND"
    MISSING = "MISSING"
    INVALID = "INVALID"

class BusinessStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
