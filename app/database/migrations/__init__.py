"""Migrations package - loads versioned migrations."""

# Import all migration modules to trigger registration with MigrationRunner
import app.database.migrations.versions.v001_initial_schema  # noqa: F401
import app.database.migrations.versions.v002_provenance_and_run_fields  # noqa: F401
import app.database.migrations.versions.v003_unique_place_per_run  # noqa: F401
