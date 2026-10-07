"""Database engine and configuration with SQLite WAL support."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config.settings import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=settings.debug,
)

# Configure SQLite for concurrency, foreign keys, and WAL mode
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from sqlalchemy import text
from datetime import datetime, timezone

import app.database.migrations  # noqa: F401
from app.database.migrations.runner import MigrationRunner

def init_db():
    """
    Initializes database schema and executes any pending versioned migrations.
    Migrations run first to ensure schema versions and history are authoritative.
    """
    # Migration runner executes versioned schema migrations as the source of truth
    applied = MigrationRunner.run_pending(engine)
    return applied

def get_schema_version() -> int:
    """Returns the current applied schema version."""
    with engine.connect() as conn:
        try:
            res = conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
            return res or 0
        except Exception:
            return 0


