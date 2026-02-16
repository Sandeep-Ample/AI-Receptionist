"""
Tests for environment variable validation.

Feature: livekit-agent-deployment
Property 1: Environment Variable Validation
Validates: Requirements 1.3, 5.3
"""

import os
import pytest
from hypothesis import given, strategies as st

from config.env_validator import (
    validate_environment,
    ConfigurationError,
    validate_database_url,
    validate_livekit_url,
    check_environment_security,
    REQUIRED_ENV_VARS,
)


# =============================================================================
# Property-Based Tests
# =============================================================================

@given(
    missing_var=st.sampled_from(REQUIRED_ENV_VARS)
)
@pytest.mark.hypothesis
def test_property_1_missing_required_variable_raises_error(missing_var):
    """
    Property 1: Environment Variable Validation
    
    For any required environment variable, if it is missing, the validation
    should fail with a ConfigurationError that mentions the missing variable.
    
    Validates: Requirements 1.3, 5.3
    """
    # Save original env vars
    original_env = {var: os.environ.get(var) for var in REQUIRED_ENV_VARS}
    
    try:
        # Set all required variables except the one we're testing
        for var in REQUIRED_ENV_VARS:
            if var != missing_var:
                os.environ[var] = f"test_value_for_{var}"
            else:
                os.environ.pop(var, None)
        
        # Validation should fail
        with pytest.raises(ConfigurationError) as exc_info:
            validate_environment()
        
        # Error message should mention the missing variable
        assert missing_var in str(exc_info.value)
    finally:
        # Restore original env vars
        for var, value in original_env.items():
            if value is not None:
                os.environ[var] = value
            else:
                os.environ.pop(var, None)


@given(
    empty_var=st.sampled_from(REQUIRED_ENV_VARS)
)
@pytest.mark.hypothesis
def test_property_1_empty_required_variable_raises_error(empty_var):
    """
    Property 1: Environment Variable Validation
    
    For any required environment variable, if it is empty (whitespace only),
    the validation should fail with a ConfigurationError.
    
    Validates: Requirements 1.3, 5.3
    """
    # Save original env vars
    original_env = {var: os.environ.get(var) for var in REQUIRED_ENV_VARS}
    
    try:
        # Set all required variables
        for var in REQUIRED_ENV_VARS:
            if var == empty_var:
                # Set the test variable to empty/whitespace
                os.environ[var] = "   "
            else:
                os.environ[var] = f"test_value_for_{var}"
        
        # Validation should fail
        with pytest.raises(ConfigurationError) as exc_info:
            validate_environment()
        
        # Error message should mention empty variables
        assert "empty" in str(exc_info.value).lower() or empty_var in str(exc_info.value)
    finally:
        # Restore original env vars
        for var, value in original_env.items():
            if value is not None:
                os.environ[var] = value
            else:
                os.environ.pop(var, None)
    assert "empty" in str(exc_info.value).lower() or empty_var in str(exc_info.value)


@given(
    database_url=st.one_of(
        st.just("postgresql://user:pass@host:5432/db"),
        st.just("postgres://user:pass@host:5432/db"),
        st.just("postgresql://user:pass@host:5432/db?sslmode=require"),
    )
)
def test_property_1_valid_database_url_formats(database_url):
    """
    Property 1: Environment Variable Validation
    
    For any valid PostgreSQL URL format, the validation should accept it.
    
    Validates: Requirements 1.3, 5.3
    """
    assert validate_database_url(database_url) is True


@given(
    livekit_url=st.one_of(
        st.just("wss://test.livekit.cloud"),
        st.just("wss://prod.livekit.cloud"),
        st.just("wss://staging-project.livekit.cloud"),
    )
)
def test_property_1_valid_livekit_url_formats(livekit_url):
    """
    Property 1: Environment Variable Validation
    
    For any valid LiveKit WSS URL, the validation should accept it.
    
    Validates: Requirements 1.3, 5.3, 8.2
    """
    assert validate_livekit_url(livekit_url) is True


# =============================================================================
# Unit Tests
# =============================================================================

def test_validate_environment_success(valid_env):
    """
    Test that validation succeeds when all required variables are present.
    """
    config = validate_environment()
    
    assert config.database_url == "postgresql://user:pass@localhost:5432/test?sslmode=require"
    assert config.livekit_url == "wss://test.livekit.cloud"
    assert config.livekit_api_key == "test_api_key"
    assert config.livekit_api_secret == "test_api_secret"
    assert config.openai_api_key == "sk-test_openai_key"
    assert config.deepgram_api_key == "test_deepgram_key"
    assert config.cartesia_api_key == "test_cartesia_key"


def test_validate_environment_missing_all_variables(clean_env):
    """
    Test that validation fails when all required variables are missing.
    """
    with pytest.raises(ConfigurationError) as exc_info:
        validate_environment()
    
    # Should mention missing variables
    assert "missing" in str(exc_info.value).lower()
    
    # Should list all required variables
    for var in REQUIRED_ENV_VARS:
        assert var in str(exc_info.value)


def test_validate_environment_optional_variables_have_defaults(valid_env):
    """
    Test that optional variables use defaults when not set.
    """
    config = validate_environment()
    
    # Should use defaults
    assert config.agent_type == "hospital"
    assert config.log_level == "INFO"
    assert config.environment == "production"


def test_validate_environment_optional_variables_can_be_overridden(valid_env):
    """
    Test that optional variables can be overridden.
    """
    valid_env.setenv("AGENT_TYPE", "hotel")
    valid_env.setenv("LOG_LEVEL", "DEBUG")
    valid_env.setenv("ENVIRONMENT", "development")
    
    config = validate_environment()
    
    assert config.agent_type == "hotel"
    assert config.log_level == "DEBUG"
    assert config.environment == "development"


def test_validate_database_url_invalid_protocol():
    """
    Test that database URL validation rejects invalid protocols.
    """
    assert validate_database_url("http://host:5432/db") is False
    assert validate_database_url("mysql://host:3306/db") is False


def test_validate_database_url_warns_without_ssl():
    """
    Test that database URL validation warns when SSL is not specified.
    """
    # Should still return True but log a warning
    result = validate_database_url("postgresql://host:5432/db")
    assert result is True


def test_validate_livekit_url_rejects_insecure():
    """
    Test that LiveKit URL validation rejects insecure WebSocket.
    
    Validates: Requirement 8.2
    """
    assert validate_livekit_url("ws://test.livekit.cloud") is False
    assert validate_livekit_url("http://test.livekit.cloud") is False


def test_check_environment_security(valid_env):
    """
    Test security checks for environment configuration.
    
    Validates: Requirements 8.1, 8.2, 8.7
    """
    checks = check_environment_security()
    
    assert "database_ssl" in checks
    assert "livekit_wss" in checks
    assert "no_secrets_in_logs" in checks
    
    # With valid_env, database has SSL and LiveKit uses WSS
    assert checks["database_ssl"] is True
    assert checks["livekit_wss"] is True


def test_configuration_error_message_clarity(clean_env):
    """
    Test that ConfigurationError provides clear, actionable error messages.
    """
    with pytest.raises(ConfigurationError) as exc_info:
        validate_environment()
    
    error_message = str(exc_info.value)
    
    # Should be clear and actionable
    assert "missing" in error_message.lower() or "required" in error_message.lower()
    assert "environment variable" in error_message.lower()
    
    # Should provide guidance
    assert "please" in error_message.lower() or "set" in error_message.lower()
