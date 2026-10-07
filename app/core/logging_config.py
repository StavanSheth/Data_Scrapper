"""Structured logging configuration for Phase 1 scraping pipeline."""

import logging
import sys
from typing import Optional

class StructuredFormatter(logging.Formatter):
    """Formats log records with standard structured key-value attributes."""
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra_parts = []
        for key in ["run_id", "stage", "place_id", "source_id", "failure_code", "status"]:
            val = getattr(record, key, None)
            if val is not None:
                extra_parts.append(f"{key}={val}")
        if extra_parts:
            return f"{base} | {' '.join(extra_parts)}"
        return base

def setup_logging(level: int = logging.INFO) -> None:
    """Configures root and application loggers with structured output."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
        root.setLevel(level)
    else:
        for h in root.handlers:
            h.setFormatter(formatter)
        root.setLevel(level)

def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    run_id: Optional[str] = None,
    stage: Optional[str] = None,
    place_id: Optional[str] = None,
    source_id: Optional[str] = None,
    failure_code: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    """Helper to log structured event metrics without leaking credentials."""
    extra = {
        "run_id": run_id,
        "stage": stage,
        "place_id": place_id,
        "source_id": source_id,
        "failure_code": failure_code,
        "status": status,
    }
    logger.log(level, message, extra=extra)
