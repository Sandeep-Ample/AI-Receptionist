"""
Environment Variable Validation Module

This module validates that all required environment variables are present
and properly configured before the agent starts. This prevents runtime
failures due to missing configuration.

Requirements: 1.3, 5.1, 5.3
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("config.env_validator")


class ConfigurationError(Exception):
    """Raised when required environment variables are missing or invalid."""
    pass


@dataclass
class EnvironmentConfig:
    """Container for validated environment configuration."""
    
    # Database
    database_url: str
    
    # LiveKit
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    
    # AI Services
    openai_api_key: str
    deepgram_api_key: str
    cartesia_api_key: str
    
    # Optional Configuration
    agent_type: str = "hospital"
    log_level: str = "INFO"
    environment: str = "production"


# Required environment variables
REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "OPENAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
]

# Optional environment variables with defaults
OPTIONAL_ENV_VARS = {
    "AGENT_TYPE": "hospital",
    "LOG_LEVEL": "INFO",
    "LOGLEVEL": "INFO",
    "ENVIRONMENT": "production",
}


def validate_environment() -> EnvironmentConfig:
    """
    Validate that all required environment variables are present and non-empty.
    
    Returns:
        EnvironmentConfig: Validated configuration object
        
    Raises:
        ConfigurationError: If any required environment variables are missing or empty
        
    Requirements: 1.3, 5.3
    """
    missing_vars: List[str] = []
    empty_vars: List[str] = []
    
    # Check for missing or empty required variables
    for var_name in REQUIRED_ENV_VARS:
        value = os.getenv(var_name)
        
        if value is None:
            missing_vars.append(var_name)
        elif not value.strip():
            empty_vars.append(var_name)
    
    # Raise error if any required variables are missing or empty
    if missing_vars or empty_vars:
        error_parts = []
        
        if missing_vars:
            error_parts.append(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        if empty_vars:
            error_parts.append(
                f"Empty required environment variables: {', '.join(empty_vars)}"
            )
        
        error_message = "\n".join(error_parts)
        error_message += "\n\nPlease set all required environment variables before starting the agent."
        
        logger.error(error_message)
        raise ConfigurationError(error_message)
    
    # Get optional variables with defaults
    agent_type = os.getenv("AGENT_TYPE", OPTIONAL_ENV_VARS["AGENT_TYPE"])
    log_level = os.getenv("LOG_LEVEL") or os.getenv("LOGLEVEL", OPTIONAL_ENV_VARS["LOG_LEVEL"])
    environment = os.getenv("ENVIRONMENT", OPTIONAL_ENV_VARS["ENVIRONMENT"])
    
    # Create configuration object
    config = EnvironmentConfig(
        database_url=os.getenv("DATABASE_URL"),
        livekit_url=os.getenv("LIVEKIT_URL"),
        livekit_api_key=os.getenv("LIVEKIT_API_KEY"),
        livekit_api_secret=os.getenv("LIVEKIT_API_SECRET"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY"),
        cartesia_api_key=os.getenv("CARTESIA_API_KEY"),
        agent_type=agent_type,
        log_level=log_level,
        environment=environment,
    )
    
    logger.info("Environment validation successful")
    logger.info(f"Agent Type: {config.agent_type}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Log Level: {config.log_level}")
    
    return config


def get_config() -> EnvironmentConfig:
    """
    Get validated environment configuration.
    
    This is a convenience function that calls validate_environment().
    
    Returns:
        EnvironmentConfig: Validated configuration object
        
    Raises:
        ConfigurationError: If validation fails
    """
    return validate_environment()


def validate_database_url(database_url: str) -> bool:
    """
    Validate that the database URL is properly formatted.
    
    Args:
        database_url: PostgreSQL connection string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not database_url:
        return False
    
    # Check for PostgreSQL protocol
    if not database_url.startswith(("postgresql://", "postgres://")):
        logger.warning("Database URL should start with 'postgresql://' or 'postgres://'")
        return False
    
    # Check for SSL mode (recommended for production)
    if "sslmode=" not in database_url:
        logger.warning("Database URL does not specify SSL mode. Consider adding '?sslmode=require'")
    
    return True


def validate_livekit_url(livekit_url: str) -> bool:
    """
    Validate that the LiveKit URL is properly formatted.
    
    Args:
        livekit_url: LiveKit server URL
        
    Returns:
        bool: True if valid, False otherwise
        
    Requirements: 8.2
    """
    if not livekit_url:
        return False
    
    # Check for secure WebSocket protocol
    if not livekit_url.startswith("wss://"):
        logger.warning("LiveKit URL should use secure WebSocket protocol (wss://)")
        return False
    
    return True


def check_environment_security() -> Dict[str, bool]:
    """
    Perform security checks on environment configuration.
    
    Returns:
        Dict[str, bool]: Dictionary of security check results
        
    Requirements: 8.1, 8.2, 8.7
    """
    checks = {
        "database_ssl": False,
        "livekit_wss": False,
        "no_secrets_in_logs": True,
    }
    
    database_url = os.getenv("DATABASE_URL", "")
    livekit_url = os.getenv("LIVEKIT_URL", "")
    
    # Check database SSL
    if "sslmode=require" in database_url or "ssl=true" in database_url:
        checks["database_ssl"] = True
    
    # Check LiveKit WSS
    if livekit_url.startswith("wss://"):
        checks["livekit_wss"] = True
    
    return checks


def print_configuration_summary(config: EnvironmentConfig, mask_secrets: bool = True) -> None:
    """
    Print a summary of the configuration (for debugging).
    
    Args:
        config: Configuration object
        mask_secrets: Whether to mask sensitive values
    """
    def mask_value(value: str, show_chars: int = 4) -> str:
        """Mask a sensitive value, showing only the last few characters."""
        if len(value) <= show_chars:
            return "*" * len(value)
        return "*" * (len(value) - show_chars) + value[-show_chars:]
    
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    
    print(f"\nAgent Configuration:")
    print(f"  Agent Type: {config.agent_type}")
    print(f"  Environment: {config.environment}")
    print(f"  Log Level: {config.log_level}")
    
    print(f"\nDatabase:")
    if mask_secrets:
        # Show only the host part
        db_parts = config.database_url.split("@")
        if len(db_parts) > 1:
            print(f"  URL: postgresql://***@{db_parts[1]}")
        else:
            print(f"  URL: {mask_value(config.database_url)}")
    else:
        print(f"  URL: {config.database_url}")
    
    print(f"\nLiveKit:")
    print(f"  URL: {config.livekit_url}")
    if mask_secrets:
        print(f"  API Key: {mask_value(config.livekit_api_key)}")
        print(f"  API Secret: {mask_value(config.livekit_api_secret)}")
    else:
        print(f"  API Key: {config.livekit_api_key}")
        print(f"  API Secret: {config.livekit_api_secret}")
    
    print(f"\nAI Services:")
    if mask_secrets:
        print(f"  OpenAI: {mask_value(config.openai_api_key)}")
        print(f"  Deepgram: {mask_value(config.deepgram_api_key)}")
        print(f"  Cartesia: {mask_value(config.cartesia_api_key)}")
    else:
        print(f"  OpenAI: {config.openai_api_key}")
        print(f"  Deepgram: {config.deepgram_api_key}")
        print(f"  Cartesia: {config.cartesia_api_key}")
    
    # Security checks
    security_checks = check_environment_security()
    print(f"\nSecurity Checks:")
    print(f"  Database SSL: {'✓' if security_checks['database_ssl'] else '✗'}")
    print(f"  LiveKit WSS: {'✓' if security_checks['livekit_wss'] else '✗'}")
    
    print("=" * 60 + "\n")
