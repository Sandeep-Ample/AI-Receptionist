"""
Tests for database migrations.

Feature: livekit-agent-deployment
Example 2: Database Migration Execution
Example 9: Migration Tool Configuration
Example 10: Migration Versioning
Property 8: Migration Rollback Support
Validates: Requirements 2.4, 9.1, 9.2, 9.4
"""

import os
import pytest
from pathlib import Path
from configparser import ConfigParser


def test_example_2_alembic_ini_exists():
    """
    Example 2: Database Migration Execution
    
    Test that alembic.ini configuration file exists.
    
    Validates: Requirements 2.4
    """
    assert os.path.exists("alembic.ini"), "alembic.ini must exist"


def test_example_2_migrations_directory_exists():
    """
    Example 2: Database Migration Execution
    
    Test that migrations directory exists.
    
    Validates: Requirements 2.4
    """
    assert os.path.exists("migrations"), "migrations directory must exist"
    assert os.path.exists("migrations/env.py"), "migrations/env.py must exist"
    assert os.path.exists("migrations/script.py.mako"), "migrations/script.py.mako must exist"


def test_example_9_alembic_configuration_valid():
    """
    Example 9: Migration Tool Configuration
    
    Test that Alembic is configured with correct settings.
    
    Validates: Requirements 9.1
    """
    config = ConfigParser()
    config.read("alembic.ini")
    
    # Check required sections
    assert "alembic" in config.sections(), "alembic.ini must have [alembic] section"
    
    # Check script location
    assert config.has_option("alembic", "script_location"), "Must specify script_location"
    script_location = config.get("alembic", "script_location")
    assert script_location == "migrations", f"script_location should be 'migrations', got '{script_location}'"
    
    # Check file template
    assert config.has_option("alembic", "file_template"), "Must specify file_template"


def test_example_9_migrations_env_uses_database_url():
    """
    Example 9: Migration Tool Configuration
    
    Test that migrations/env.py is configured to use DATABASE_URL.
    
    Validates: Requirements 9.1
    """
    with open("migrations/env.py", "r") as f:
        content = f.read()
    
    # Should read DATABASE_URL from environment
    assert "DATABASE_URL" in content, "env.py should read DATABASE_URL"
    assert "os.getenv" in content or "os.environ" in content, "env.py should use os.getenv or os.environ"
    
    # Should set sqlalchemy.url
    assert "sqlalchemy.url" in content, "env.py should configure sqlalchemy.url"


def test_example_10_migration_files_follow_naming_convention():
    """
    Example 10: Migration Versioning
    
    Test that migration files follow the naming convention.
    
    Validates: Requirements 9.2
    """
    migrations_dir = Path("migrations/versions")
    
    if migrations_dir.exists():
        migration_files = list(migrations_dir.glob("*.py"))
        migration_files = [f for f in migration_files if f.name != "__init__.py"]
        
        for migration_file in migration_files:
            # Should have .py extension
            assert migration_file.suffix == ".py", f"Migration file should be .py: {migration_file}"
            
            # Should contain revision ID in filename or content
            with open(migration_file, "r") as f:
                content = f.read()
            
            assert "revision:" in content or "revision =" in content, \
                f"Migration file should have revision ID: {migration_file}"
            assert "down_revision:" in content or "down_revision =" in content, \
                f"Migration file should have down_revision: {migration_file}"


def test_example_10_initial_migration_exists():
    """
    Example 10: Migration Versioning
    
    Test that initial migration exists.
    
    Validates: Requirements 9.2
    """
    migrations_dir = Path("migrations/versions")
    assert migrations_dir.exists(), "migrations/versions directory must exist"
    
    # Check for initial migration
    initial_migration = migrations_dir / "001_initial_hospital_schema.py"
    assert initial_migration.exists(), "Initial migration (001) must exist"


def test_example_10_migration_has_unique_revision_id():
    """
    Example 10: Migration Versioning
    
    Test that each migration has a unique revision identifier.
    
    Validates: Requirements 9.2
    """
    migrations_dir = Path("migrations/versions")
    
    if not migrations_dir.exists():
        pytest.skip("No migrations directory")
    
    migration_files = list(migrations_dir.glob("*.py"))
    migration_files = [f for f in migration_files if f.name != "__init__.py"]
    
    revision_ids = set()
    
    for migration_file in migration_files:
        with open(migration_file, "r") as f:
            content = f.read()
        
        # Extract revision ID
        for line in content.split("\n"):
            if line.strip().startswith("revision:") or line.strip().startswith("revision ="):
                # Extract the revision value
                if "=" in line:
                    revision = line.split("=")[1].strip().strip("'\"")
                else:
                    revision = line.split(":")[1].strip().strip("'\"")
                
                # Check for duplicates
                assert revision not in revision_ids, \
                    f"Duplicate revision ID found: {revision} in {migration_file}"
                
                revision_ids.add(revision)
                break


def test_initial_migration_structure():
    """
    Test that initial migration has correct structure.
    
    Validates: Requirements 2.4, 9.2
    """
    migration_file = Path("migrations/versions/001_initial_hospital_schema.py")
    
    with open(migration_file, "r") as f:
        content = f.read()
    
    # Should have upgrade function
    assert "def upgrade()" in content, "Migration must have upgrade() function"
    
    # Should have downgrade function
    assert "def downgrade()" in content, "Migration must have downgrade() function"
    
    # Should create tables
    assert "create_table" in content or "CREATE TABLE" in content, \
        "Migration should create tables"
    
    # Should create indexes
    assert "create_index" in content or "CREATE INDEX" in content, \
        "Migration should create indexes"


def test_property_8_migration_has_rollback_support():
    """
    Property 8: Migration Rollback Support
    
    For any database migration, there must exist a corresponding downgrade
    function that can reverse the changes.
    
    Validates: Requirements 9.4
    """
    migrations_dir = Path("migrations/versions")
    
    if not migrations_dir.exists():
        pytest.skip("No migrations directory")
    
    migration_files = list(migrations_dir.glob("*.py"))
    migration_files = [f for f in migration_files if f.name != "__init__.py"]
    
    for migration_file in migration_files:
        with open(migration_file, "r") as f:
            content = f.read()
        
        # Check for upgrade function
        has_upgrade = "def upgrade()" in content
        
        # Check for downgrade function
        has_downgrade = "def downgrade()" in content
        
        assert has_upgrade, f"Migration {migration_file} must have upgrade() function"
        assert has_downgrade, f"Migration {migration_file} must have downgrade() function"
        
        # Downgrade should not just pass (should actually do something)
        # Extract downgrade function
        downgrade_start = content.find("def downgrade()")
        if downgrade_start != -1:
            # Find the next function or end of file
            next_def = content.find("\ndef ", downgrade_start + 1)
            if next_def == -1:
                downgrade_content = content[downgrade_start:]
            else:
                downgrade_content = content[downgrade_start:next_def]
            
            # Should have more than just "pass"
            lines = [line.strip() for line in downgrade_content.split("\n") if line.strip()]
            non_empty_lines = [line for line in lines if line and not line.startswith("#")]
            
            # Should have at least the function definition and some operations
            assert len(non_empty_lines) > 2, \
                f"Migration {migration_file} downgrade() should have actual rollback operations, not just 'pass'"


def test_migration_creates_required_tables():
    """
    Test that initial migration creates all required tables.
    
    Validates: Requirements 2.4
    """
    migration_file = Path("migrations/versions/001_initial_hospital_schema.py")
    
    with open(migration_file, "r") as f:
        content = f.read()
    
    required_tables = [
        "patient_account",
        "patient",
        "doctor",
        "specialty",
        "symptoms",
        "appointment",
        "doc_shift",
        "user_memory",
        "call_session",
    ]
    
    for table in required_tables:
        assert table in content, f"Migration should create {table} table"


def test_migration_creates_indexes():
    """
    Test that initial migration creates performance indexes.
    
    Validates: Requirements 2.4
    """
    migration_file = Path("migrations/versions/001_initial_hospital_schema.py")
    
    with open(migration_file, "r") as f:
        content = f.read()
    
    required_indexes = [
        "idx_patient_account_mobile",
        "idx_doctor_name",
        "idx_appointments_datetime",
        "idx_appointments_patient",
        "idx_appointments_doctor",
    ]
    
    for index in required_indexes:
        assert index in content, f"Migration should create {index} index"


def test_migration_creates_enum_types():
    """
    Test that initial migration creates required ENUM types.
    
    Validates: Requirements 2.4
    """
    migration_file = Path("migrations/versions/001_initial_hospital_schema.py")
    
    with open(migration_file, "r") as f:
        content = f.read()
    
    required_enums = [
        "appointment_status_enum",
        "shift_status_enum",
        "doctor_status_enum",
        "gender_enum",
        "weekday_enum",
    ]
    
    for enum in required_enums:
        assert enum in content, f"Migration should create {enum} type"


def test_migration_downgrade_drops_tables():
    """
    Test that migration downgrade properly drops tables.
    
    Validates: Requirements 9.4
    """
    migration_file = Path("migrations/versions/001_initial_hospital_schema.py")
    
    with open(migration_file, "r") as f:
        content = f.read()
    
    # Find downgrade function
    downgrade_start = content.find("def downgrade()")
    assert downgrade_start != -1, "Migration must have downgrade function"
    
    downgrade_content = content[downgrade_start:]
    
    # Should drop tables
    assert "drop_table" in downgrade_content or "DROP TABLE" in downgrade_content, \
        "Downgrade should drop tables"
    
    # Should drop enum types
    assert "DROP TYPE" in downgrade_content, \
        "Downgrade should drop enum types"
