"""
Tests for configuration file presence and validity.

Feature: livekit-agent-deployment
Example 6: Configuration Files Presence
Validates: Requirements 5.2
"""

import os
import pytest
import yaml


def test_example_6_livekit_yaml_exists():
    """
    Example 6: Configuration Files Presence
    
    Test that livekit.yaml exists in the project root.
    
    Validates: Requirements 5.2
    """
    assert os.path.exists("livekit.yaml"), "livekit.yaml file must exist"


def test_example_6_dockerfile_exists():
    """
    Example 6: Configuration Files Presence
    
    Test that Dockerfile exists in the project root.
    
    Validates: Requirements 5.2
    """
    assert os.path.exists("Dockerfile"), "Dockerfile must exist"


def test_example_6_requirements_txt_exists():
    """
    Example 6: Configuration Files Presence
    
    Test that requirements.txt exists in the project root.
    
    Validates: Requirements 5.2
    """
    assert os.path.exists("requirements.txt"), "requirements.txt must exist"


def test_example_6_dockerignore_exists():
    """
    Example 6: Configuration Files Presence
    
    Test that .dockerignore exists to optimize Docker builds.
    
    Validates: Requirements 5.2
    """
    assert os.path.exists(".dockerignore"), ".dockerignore must exist"


def test_example_6_env_example_exists():
    """
    Example 6: Configuration Files Presence
    
    Test that .env.example exists as a template.
    
    Validates: Requirements 5.2
    """
    assert os.path.exists(".env.example"), ".env.example must exist"


def test_livekit_yaml_valid_structure():
    """
    Test that livekit.yaml has valid YAML structure and required fields.
    
    Validates: Requirements 3.4
    """
    with open("livekit.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Check required top-level fields
    assert "agent" in config, "livekit.yaml must have 'agent' section"
    assert "build" in config, "livekit.yaml must have 'build' section"
    assert "runtime" in config, "livekit.yaml must have 'runtime' section"
    assert "resources" in config, "livekit.yaml must have 'resources' section"
    
    # Check agent section
    assert "name" in config["agent"], "agent section must have 'name'"
    assert "version" in config["agent"], "agent section must have 'version'"
    
    # Check build section
    assert "dockerfile" in config["build"], "build section must have 'dockerfile'"
    assert "context" in config["build"], "build section must have 'context'"
    
    # Check runtime section
    assert "python_version" in config["runtime"], "runtime section must have 'python_version'"


def test_dockerfile_has_required_instructions():
    """
    Test that Dockerfile contains required instructions.
    
    Validates: Requirements 5.2
    """
    with open("Dockerfile", "r") as f:
        content = f.read()
    
    # Check for required instructions
    assert "FROM python:" in content, "Dockerfile must specify Python base image"
    assert "WORKDIR" in content, "Dockerfile must set working directory"
    assert "COPY requirements.txt" in content, "Dockerfile must copy requirements.txt"
    assert "RUN pip install" in content, "Dockerfile must install dependencies"
    assert "CMD" in content or "ENTRYPOINT" in content, "Dockerfile must specify entry point"


def test_requirements_txt_has_core_dependencies():
    """
    Test that requirements.txt includes core dependencies.
    
    Validates: Requirements 5.2
    """
    with open("requirements.txt", "r") as f:
        content = f.read()
    
    # Check for core dependencies
    required_packages = [
        "livekit-agents",
        "livekit-plugins-deepgram",
        "livekit-plugins-openai",
        "livekit-plugins-cartesia",
        "livekit-plugins-silero",
        "asyncpg",
        "alembic",
        "python-dotenv",
    ]
    
    for package in required_packages:
        assert package in content, f"requirements.txt must include {package}"


def test_env_example_has_all_required_variables():
    """
    Test that .env.example includes all required environment variables.
    
    Validates: Requirements 5.2
    """
    with open(".env.example", "r") as f:
        content = f.read()
    
    required_vars = [
        "DATABASE_URL",
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY",
    ]
    
    for var in required_vars:
        assert var in content, f".env.example must include {var}"


def test_env_example_has_no_real_secrets():
    """
    Test that .env.example doesn't contain real secrets.
    
    Validates: Requirements 5.5
    """
    with open(".env.example", "r") as f:
        content = f.read()
    
    # Check for patterns that might indicate real secrets
    dangerous_patterns = [
        "sk-proj-",  # OpenAI project keys
        "sk-[a-zA-Z0-9]{48}",  # OpenAI key pattern
    ]
    
    # Should contain placeholder text
    assert "your_" in content or "your-" in content, ".env.example should use placeholders"
    assert "example" in content.lower() or "template" in content.lower(), ".env.example should indicate it's a template"


def test_dockerignore_excludes_sensitive_files():
    """
    Test that .dockerignore excludes sensitive files.
    
    Validates: Requirements 5.2, 5.5
    """
    with open(".dockerignore", "r") as f:
        content = f.read()
    
    # Should exclude sensitive files
    sensitive_patterns = [
        ".env",
        ".git",
        "*.log",
        "__pycache__",
    ]
    
    for pattern in sensitive_patterns:
        assert pattern in content, f".dockerignore should exclude {pattern}"
