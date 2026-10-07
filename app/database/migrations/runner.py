"""Database migration runner for managing schema evolution across slices."""

import logging
from typing import List, Callable, Tuple
from sqlalchemy import text, Connection, Engine
from datetime import datetime, timezone

logger = logging.getLogger("db_migrations")

class Migration:
    def __init__(self, version: int, name: str, upgrade_fn: Callable[[Connection], None]):
        self.version = version
        self.name = name
        self.upgrade_fn = upgrade_fn

class MigrationRunner:
    """Manages transactional execution of pending database migrations."""
    _migrations: List[Migration] = []

    @classmethod
    def register(cls, version: int, name: str):
        """Decorator to register a versioned migration."""
        def decorator(fn: Callable[[Connection], None]):
            cls._migrations.append(Migration(version, name, fn))
            cls._migrations.sort(key=lambda m: m.version)
            return fn
        return decorator

    @classmethod
    def run_pending(cls, engine: Engine) -> int:
        """Executes all unapplied registered migrations in ascending version order."""
        with engine.begin() as conn:
            # Ensure migration ledger table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
            """))

            # Determine currently applied version
            current = conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar() or 0
            applied_count = 0

            for m in cls._migrations:
                if m.version > current:
                    logger.info("Applying database migration %03d: %s", m.version, m.name)
                    m.upgrade_fn(conn)
                    now_iso = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        text("INSERT INTO schema_version (version, name, applied_at) VALUES (:ver, :name, :ts)"),
                        {"ver": m.version, "name": m.name, "ts": now_iso}
                    )
                    applied_count += 1

            return applied_count
