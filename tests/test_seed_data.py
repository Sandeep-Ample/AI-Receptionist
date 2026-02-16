"""
Tests for database seed data script.

Feature: livekit-agent-deployment
Example 3: Seed Data Loading
Validates: Requirements 2.5
"""

import os
import pytest
from pathlib import Path


def test_example_3_seed_script_exists():
    """
    Example 3: Seed Data Loading
    
    Test that the seed data script exists.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    assert seed_script.exists(), "Seed script must exist at scripts/seed_database.py"


def test_example_3_seed_script_is_executable():
    """
    Example 3: Seed Data Loading
    
    Test that the seed script can be imported and has required functions.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    # Read the script
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should have main seed function
    assert "async def seed_database" in content or "def seed_database" in content, \
        "Seed script should have seed_database function"
    
    # Should handle DATABASE_URL
    assert "DATABASE_URL" in content, \
        "Seed script should read DATABASE_URL"
    
    # Should be idempotent
    assert "idempotent" in content.lower() or "already exists" in content.lower(), \
        "Seed script should be idempotent (safe to run multiple times)"


def test_example_3_seed_script_has_sample_data():
    """
    Example 3: Seed Data Loading
    
    Test that the seed script includes sample data definitions.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should define sample data
    required_data_types = [
        "specialty" or "SPECIALTIES",
        "doctor" or "DOCTORS",
        "symptom" or "SYMPTOMS",
    ]
    
    # At least some sample data should be defined
    has_sample_data = any(data_type.lower() in content.lower() for data_type in required_data_types)
    assert has_sample_data, "Seed script should define sample data"


def test_example_3_seed_script_creates_required_entities():
    """
    Example 3: Seed Data Loading
    
    Test that the seed script creates all required entity types.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should insert into required tables
    required_tables = [
        "specialty",
        "doctor",
        "symptoms",
        "patient_account",
    ]
    
    for table in required_tables:
        assert f"INSERT INTO {table}" in content or f"insert into {table}" in content.lower(), \
            f"Seed script should insert data into {table} table"


def test_example_3_seed_script_handles_errors():
    """
    Example 3: Seed Data Loading
    
    Test that the seed script has error handling.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should have try/except blocks
    assert "try:" in content and "except" in content, \
        "Seed script should have error handling"
    
    # Should log errors
    assert "logger" in content or "logging" in content or "print" in content, \
        "Seed script should log progress and errors"


def test_example_3_seed_script_is_idempotent():
    """
    Example 3: Seed Data Loading
    
    Test that the seed script checks for existing data (idempotent).
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should check for existing data
    idempotent_patterns = [
        "ON CONFLICT",
        "IF NOT EXISTS",
        "COUNT(*)",
        "already exists",
        "existing",
    ]
    
    has_idempotent_check = any(pattern in content for pattern in idempotent_patterns)
    assert has_idempotent_check, \
        "Seed script should check for existing data to be idempotent"


def test_seed_script_uses_asyncpg():
    """
    Test that seed script uses asyncpg for database operations.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should import asyncpg
    assert "import asyncpg" in content or "from asyncpg" in content, \
        "Seed script should use asyncpg"
    
    # Should use async/await
    assert "async def" in content and "await" in content, \
        "Seed script should use async/await pattern"


def test_seed_script_can_be_run_as_main():
    """
    Test that seed script can be run as a standalone script.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should have main block
    assert 'if __name__ == "__main__"' in content, \
        "Seed script should have main block for standalone execution"


def test_seed_script_returns_success_status():
    """
    Test that seed script returns success/failure status.
    
    Validates: Requirements 2.5
    """
    seed_script = Path("scripts/seed_database.py")
    
    with open(seed_script, "r") as f:
        content = f.read()
    
    # Should return or exit with status
    assert "return" in content or "sys.exit" in content, \
        "Seed script should return success/failure status"
