"""Application constants for Business Intelligence Scraper."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = DATA_DIR / "database"
DEFAULT_DB_PATH = DATABASE_DIR / "scraper.db"

# Ensure database directory exists
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Run Status Constants
STATUS_CREATED = "CREATED"
STATUS_QUEUED = "QUEUED"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"

VALID_RUN_STATUSES = {
    STATUS_CREATED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_PARTIAL,
    STATUS_FAILED,
    STATUS_CANCELLED,
}

# Source types
SOURCE_GOOGLE = "GOOGLE"

# Field status values
FIELD_FOUND = "FOUND"
FIELD_MISSING = "MISSING"
FIELD_INVALID = "INVALID"

# Legal suffixes to remove in normalization
LEGAL_SUFFIXES = [
    "pvt ltd",
    "private limited",
    "pvt. ltd.",
    "llp",
    "ltd",
    "limited",
    "inc",
    "inc.",
    "corp",
    "corporation",
    "co",
    "co.",
    "company",
]
