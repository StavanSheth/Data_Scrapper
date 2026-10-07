"""Migration 2: Ensure provenance audit fields and run categories exist in existing databases."""

from sqlalchemy import text, Connection
from app.database.migrations.runner import MigrationRunner

@MigrationRunner.register(2, "add_provenance_audit_fields_and_categories")
def upgrade(conn: Connection):
    """
    Safely adds raw_fragment, validator_rule, and categories columns if migrating an existing SQLite database.
    """
    # 1. Check columns in field_provenance
    prov_columns = [
        row[1] for row in conn.execute(text("PRAGMA table_info(field_provenance)")).fetchall()
    ]
    if "raw_fragment" not in prov_columns:
        conn.execute(text("ALTER TABLE field_provenance ADD COLUMN raw_fragment TEXT;"))
    if "validator_rule" not in prov_columns:
        conn.execute(text("ALTER TABLE field_provenance ADD COLUMN validator_rule TEXT;"))

    # 2. Check columns in runs
    runs_columns = [
        row[1] for row in conn.execute(text("PRAGMA table_info(runs)")).fetchall()
    ]
    if "categories" not in runs_columns:
        conn.execute(text("ALTER TABLE runs ADD COLUMN categories TEXT;"))
