"""
Tests for health check functionality.

Includes:
- Property-based tests for health check accuracy
- Example tests for startup connectivity verification
- Unit tests for individual health checks
"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, settings

from health_check import (
    check_database_health,
    check_livekit_health,
    check_ai_service_health,
    perform_health_check,
    verify_startup_connectivity,
    get_health_status_code,
)


# --- Property-Based Tests ---

# Feature: livekit-agent-deployment, Property 5: Health Check Accuracy
@given(
    db_healthy=st.booleans(),
    livekit_healthy=st.booleans(),
    ai_services_healthy=st.booleans(),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_5_health_check_accuracy(db_healthy, livekit_healthy, ai_services_healthy):
    """
    **Property 5: Health Check Accuracy**
    **Validates: Requirements 6.4**
    
    For any system state (all services healthy, database down, AI service
    unavailable), the health check endpoint should return a status that
    accurately reflects the actual state of all dependencies.
    """
    # Mock all health check functions
    with patch("health_check.check_database_health") as mock_db, \
         patch("health_check.check_livekit_health") as mock_livekit, \
         patch("health_check.check_ai_service_health") as mock_ai:
        
        # Configure mocks based on test parameters
        mock_db.return_value = {"healthy": db_healthy}
        mock_livekit.return_value = {"healthy": livekit_healthy}
        mock_ai.return_value = {"healthy": ai_services_healthy}
        
        # Perform health check
        health = await perform_health_check()
        
        # Verify overall status matches component states
        expected_healthy = db_healthy and livekit_healthy and ai_services_healthy
        actual_healthy = health["status"] == "healthy"
        
        assert actual_healthy == expected_healthy, \
            f"Health check status should be {'healthy' if expected_healthy else 'unhealthy'}"
        
        # Verify all components are checked
        assert "database" in health["checks"]
        assert "livekit" in health["checks"]
        assert "deepgram" in health["checks"]
        assert "openai" in health["checks"]
        assert "cartesia" in health["checks"]
        
        # Verify individual component statuses
        assert health["checks"]["database"]["healthy"] == db_healthy
        assert health["checks"]["livekit"]["healthy"] == livekit_healthy
        # All AI services use the same mock, so they should all match
        assert health["checks"]["deepgram"]["healthy"] == ai_services_healthy
        assert health["checks"]["openai"]["healthy"] == ai_services_healthy
        assert health["checks"]["cartesia"]["healthy"] == ai_services_healthy
        
        # Verify HTTP status code
        status_code = get_health_status_code(health)
        expected_code = 200 if expected_healthy else 503
        assert status_code == expected_code


# --- Example Tests ---

# Example 1: Agent Startup Connectivity Verification
@pytest.mark.asyncio
async def test_example_1_agent_startup_connectivity_verification():
    """
    **Example 1: Agent Startup Connectivity Verification**
    **Validates: Requirements 1.6**
    
    Test that agent startup performs connectivity checks to all required
    services (Database, LiveKit, STT, LLM, TTS).
    """
    # Mock all services as healthy
    with patch("health_check.check_database_health") as mock_db, \
         patch("health_check.check_livekit_health") as mock_livekit, \
         patch("health_check.check_ai_service_health") as mock_ai:
        
        mock_db.return_value = {"healthy": True, "connected": True}
        mock_livekit.return_value = {"healthy": True, "configured": True}
        mock_ai.return_value = {"healthy": True, "configured": True}
        
        # Verify startup connectivity
        result = await verify_startup_connectivity()
        
        # Should return True when all services are healthy
        assert result is True
        
        # Verify all checks were called
        mock_db.assert_called_once()
        mock_livekit.assert_called_once()
        # AI service check is called 3 times (Deepgram, OpenAI, Cartesia)
        assert mock_ai.call_count == 3


@pytest.mark.asyncio
async def test_startup_connectivity_fails_when_service_down():
    """Test that startup connectivity verification fails when a service is down."""
    # Mock database as unhealthy
    with patch("health_check.check_database_health") as mock_db, \
         patch("health_check.check_livekit_health") as mock_livekit, \
         patch("health_check.check_ai_service_health") as mock_ai:
        
        mock_db.return_value = {"healthy": False, "error": "Connection refused"}
        mock_livekit.return_value = {"healthy": True, "configured": True}
        mock_ai.return_value = {"healthy": True, "configured": True}
        
        # Verify startup connectivity
        result = await verify_startup_connectivity()
        
        # Should return False when any service is unhealthy
        assert result is False


# --- Unit Tests ---

@pytest.mark.asyncio
async def test_check_database_health_when_not_configured():
    """Test database health check when database is not configured."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove DATABASE_URL
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        
        with patch("health_check.get_database_connection") as mock_get_db:
            mock_db = MagicMock()
            mock_db.is_enabled = False
            mock_get_db.return_value = mock_db
            
            health = await check_database_health()
            
            assert health["healthy"] is False
            assert health["connected"] is False
            assert "not configured" in health["error"].lower()


@pytest.mark.asyncio
async def test_check_livekit_health_when_configured():
    """Test LiveKit health check when properly configured."""
    with patch.dict(os.environ, {
        "LIVEKIT_URL": "wss://test.livekit.cloud",
        "LIVEKIT_API_KEY": "test_key",
    }):
        health = await check_livekit_health()
        
        assert health["healthy"] is True
        assert health["configured"] is True


@pytest.mark.asyncio
async def test_check_livekit_health_when_not_configured():
    """Test LiveKit health check when not configured."""
    with patch.dict(os.environ, {}, clear=True):
        health = await check_livekit_health()
        
        assert health["healthy"] is False
        assert health["configured"] is False
        assert "not configured" in health["error"].lower()


@pytest.mark.asyncio
async def test_check_ai_service_health_when_configured():
    """Test AI service health check when API key is configured."""
    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test123"}):
        health = await check_ai_service_health("TestService", "TEST_API_KEY")
        
        assert health["healthy"] is True
        assert health["configured"] is True


@pytest.mark.asyncio
async def test_check_ai_service_health_when_not_configured():
    """Test AI service health check when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        health = await check_ai_service_health("TestService", "MISSING_KEY")
        
        assert health["healthy"] is False
        assert health["configured"] is False
        assert "not configured" in health["error"].lower()


@pytest.mark.asyncio
async def test_perform_health_check_returns_all_components():
    """Test that perform_health_check checks all required components."""
    with patch("health_check.check_database_health") as mock_db, \
         patch("health_check.check_livekit_health") as mock_livekit, \
         patch("health_check.check_ai_service_health") as mock_ai:
        
        mock_db.return_value = {"healthy": True}
        mock_livekit.return_value = {"healthy": True}
        mock_ai.return_value = {"healthy": True}
        
        health = await perform_health_check()
        
        # Verify all components are present
        assert "database" in health["checks"]
        assert "livekit" in health["checks"]
        assert "deepgram" in health["checks"]
        assert "openai" in health["checks"]
        assert "cartesia" in health["checks"]
        
        # Verify timestamp is present
        assert "timestamp" in health
        assert health["timestamp"].endswith("Z")


def test_get_health_status_code_returns_200_when_healthy():
    """Test that status code is 200 when all services are healthy."""
    health = {"status": "healthy"}
    assert get_health_status_code(health) == 200


def test_get_health_status_code_returns_503_when_unhealthy():
    """Test that status code is 503 when any service is unhealthy."""
    health = {"status": "unhealthy"}
    assert get_health_status_code(health) == 503
