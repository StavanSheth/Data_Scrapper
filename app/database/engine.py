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

def init_db():
    """
    Initializes database schema, creates SQLite tables, and establishes version tracking.
    Enables safe, incremental migrations for Slice 2 and beyond.
    """
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """))
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            text("INSERT OR IGNORE INTO schema_version (version, name, applied_at) VALUES (1, 'slice_1_initial', :applied_at)"),
            {"applied_at": now_iso}
        )

def get_schema_version() -> int:
    """Returns the current applied schema version."""
    with engine.connect() as conn:
        res = conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        return res or 0


