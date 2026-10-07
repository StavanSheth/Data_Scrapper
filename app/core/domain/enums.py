"""Domain enums for Business Intelligence Scraper."""

from enum import Enum

class RunStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    INTERRUPTED = "INTERRUPTED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

# Authoritative run lifecycle state machine transitions
# Any transition outside this mapping is rejected to prevent state corruption.
VALID_STATUS_TRANSITIONS = {
    RunStatus.CREATED: {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED, RunStatus.INTERRUPTED},
    RunStatus.RUNNING: {
        RunStatus.INTERRUPTED,
        RunStatus.COMPLETED,
        RunStatus.PARTIAL,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.INTERRUPTED: {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.FAILED: {RunStatus.QUEUED, RunStatus.RUNNING},
    RunStatus.CANCELLED: {RunStatus.QUEUED, RunStatus.RUNNING},
    RunStatus.PARTIAL: {RunStatus.QUEUED, RunStatus.RUNNING},  # Resume allowed if limit not reached
    RunStatus.COMPLETED: set(),  # Terminal state: COMPLETED cannot transition to anything
}

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
