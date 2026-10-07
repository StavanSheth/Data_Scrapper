"""Field state model for tracking extraction and enrichment lifecycle."""

from enum import Enum
from typing import NamedTuple, Any, Optional

class FieldState(str, Enum):
    FOUND = "FOUND"
    MISSING = "MISSING"
    INVALID = "INVALID"
    NOT_REQUESTED = "NOT_REQUESTED"
    NOT_AVAILABLE = "NOT_AVAILABLE"

class FieldValue(NamedTuple):
    name: str
    value: Any
    state: FieldState
    confidence: float = 1.0
    error: Optional[str] = None
