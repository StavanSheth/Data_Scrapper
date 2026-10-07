"""Baseline initial schema migration (Slice 1)."""

from sqlalchemy import text, Connection
from app.database.migrations.runner import MigrationRunner

@MigrationRunner.register(1, "slice_1_initial_schema")
def upgrade(conn: Connection):
    """
    Applies initial baseline tables and performance indexes for Slice 1.
    """
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            city_input TEXT NOT NULL,
            city_normalized TEXT NOT NULL,
            category TEXT,
            categories TEXT,
            category_mode TEXT NOT NULL DEFAULT 'selected',
            confidence_threshold REAL NOT NULL DEFAULT 0.80,
            requested_limit INTEGER NOT NULL DEFAULT 100,
            status TEXT NOT NULL DEFAULT 'CREATED',
            started_at TEXT,
            completed_at TEXT,
            cancelled_at TEXT,
            total_google_records INTEGER DEFAULT 0,
            total_platform_records INTEGER DEFAULT 0,
            total_matched INTEGER DEFAULT 0,
            total_google_unmatched INTEGER DEFAULT 0,
            total_platform_unmatched INTEGER DEFAULT 0,
            records_discovered INTEGER DEFAULT 0,
            records_saved INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TEXT NOT NULL
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS source_records (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            platform_id TEXT,
            source_type TEXT NOT NULL DEFAULT 'GOOGLE',
            source_url TEXT,
            external_id TEXT,
            raw_name TEXT,
            raw_address TEXT,
            raw_phone TEXT,
            raw_email TEXT,
            raw_website TEXT,
            raw_category TEXT,
            raw_latitude REAL,
            raw_longitude REAL,
            raw_rating REAL,
            raw_review_count INTEGER,
            raw_payload TEXT,
            extraction_status TEXT NOT NULL DEFAULT 'SUCCESS',
            scraped_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS businesses (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'GOOGLE',
            source_record_id TEXT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            category TEXT,
            subcategory TEXT,
            address TEXT,
            street TEXT,
            locality TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT,
            latitude REAL,
            longitude REAL,
            phone TEXT,
            normalized_phone TEXT,
            email TEXT,
            website TEXT,
            website_domain TEXT,
            website_status TEXT,
            rating REAL,
            review_count INTEGER,
            google_place_id TEXT,
            google_profile_url TEXT,
            opening_hours TEXT,
            status TEXT NOT NULL DEFAULT 'VALID',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE,
            FOREIGN KEY (source_record_id) REFERENCES source_records (id)
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS field_provenance (
            id TEXT PRIMARY KEY,
            business_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT,
            source_type TEXT NOT NULL,
            source_url TEXT,
            source_record_id TEXT,
            extraction_method TEXT,
            confidence REAL,
            raw_fragment TEXT,
            validator_rule TEXT,
            extracted_at TEXT NOT NULL,
            FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );
    """))

    # Compound and search indexes
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_businesses_run_name ON businesses (run_id, normalized_name);"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_businesses_run_created ON businesses (run_id, created_at);"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_businesses_run_city ON businesses (run_id, city);"))
