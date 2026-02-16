"""
Pytest configuration and fixtures for testing.
"""

import os
import pytest
from hypothesis import settings, Verbosity

# Configure Hypothesis for property-based testing
settings.register_profile("ci", max_examples=100, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=50)
settings.load_profile("ci" if os.getenv("CI") else "dev")


@pytest.fixture
def clean_env(monkeypatch):
    """
    Fixture that provides a clean environment for testing.
    Removes all agent-related environment variables.
    """
    env_vars_to_remove = [
        "DATABASE_URL",
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY",
        "AGENT_TYPE",
        "LOG_LEVEL",
        "LOGLEVEL",
        "ENVIRONMENT",
    ]
    
    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)
    
    return monkeypatch


@pytest.fixture
def valid_env(monkeypatch):
    """
    Fixture that provides a valid environment configuration for testing.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test?sslmode=require")
    monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "test_api_key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test_api_secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test_openai_key")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test_deepgram_key")
    monkeypatch.setenv("CARTESIA_API_KEY", "test_cartesia_key")
    
    return monkeypatch
