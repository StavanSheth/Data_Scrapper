"""Migration 4: Add records_attempted and records_duplicates to runs table."""

from sqlalchemy import text, Connection
from app.database.migrations.runner import MigrationRunner

@MigrationRunner.register(4, "add_run_accounting_fields")
def upgrade(conn: Connection):
    """
    Safely adds records_attempted and records_duplicates to runs table for existing SQLite databases.
    """
    existing_cols = [
        row[1] for row in conn.execute(text("PRAGMA table_info(runs)")).fetchall()
    ]
    if "records_attempted" not in existing_cols:
        conn.execute(text("ALTER TABLE runs ADD COLUMN records_attempted INTEGER DEFAULT 0;"))
    if "records_duplicates" not in existing_cols:
        conn.execute(text("ALTER TABLE runs ADD COLUMN records_duplicates INTEGER DEFAULT 0;"))
