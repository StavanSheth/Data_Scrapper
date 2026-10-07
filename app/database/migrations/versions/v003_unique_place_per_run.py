"""Migration 3: Add database unique constraint on (run_id, google_place_id) for strong deduplication."""

from sqlalchemy import text, Connection
from app.database.migrations.runner import MigrationRunner

@MigrationRunner.register(3, "enforce_unique_place_per_run")
def upgrade(conn: Connection):
    """
    Enforces atomic database-level deduplication: prevents duplicate insertions of the same
    Google Place ID within the same run, even under concurrent worker execution.
    """
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_businesses_run_place_id 
        ON businesses (run_id, google_place_id) 
        WHERE google_place_id IS NOT NULL;
    """))
