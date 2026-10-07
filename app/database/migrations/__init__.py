"""Migrations package - loads versioned migrations."""

# Import all migration modules to trigger registration with MigrationRunner
import app.database.migrations.versions.v001_initial_schema  # noqa: F401
