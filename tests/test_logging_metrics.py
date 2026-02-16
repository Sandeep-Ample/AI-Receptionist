"""
Tests for logging configuration and metrics collection.

Includes:
- Property-based tests for event logging completeness
- Property-based tests for metrics collection
- Unit tests for secret sanitization
"""

import json
import logging
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings

from logging_config import (
    configure_logging,
    sanitize_message,
    JSONFormatter,
    MetricsCollector,
    get_metrics_collector,
)


# --- Unit Tests for Secret Sanitization ---

def test_sanitize_openai_key():
    """Test that OpenAI API keys are sanitized."""
    message = "Using API key: sk-1234567890abcdefghij"
    sanitized = sanitize_message(message)
    assert "sk-1234567890abcdefghij" not in sanitized
    assert "sk-***" in sanitized


def test_sanitize_bearer_token():
    """Test that Bearer tokens are sanitized."""
    message = "Authorization: Bearer abc123def456"
    sanitized = sanitize_message(message)
    assert "abc123def456" not in sanitized
    assert "Bearer ***" in sanitized


def test_sanitize_api_key():
    """Test that generic API keys are sanitized."""
    message = 'api_key="my_secret_key_123"'
    sanitized = sanitize_message(message)
    assert "my_secret_key_123" not in sanitized
    assert "***" in sanitized


def test_sanitize_password():
    """Test that passwords are sanitized."""
    message = 'password="super_secret_pass"'
    sanitized = sanitize_message(message)
    assert "super_secret_pass" not in sanitized
    assert "***" in sanitized


def test_sanitize_preserves_safe_content():
    """Test that non-secret content is preserved."""
    message = "User logged in successfully"
    sanitized = sanitize_message(message)
    assert sanitized == message


# --- Property-Based Tests ---

# Feature: livekit-agent-deployment, Property 2: Event Logging Completeness
@given(
    event_type=st.sampled_from(["agent_startup", "voice_interaction", "database_query", "error"]),
    session_id=st.text(min_size=1, max_size=50),
    message=st.text(min_size=1, max_size=200),
)
@settings(max_examples=100)
def test_property_2_event_logging_completeness(event_type, session_id, message):
    """
    **Property 2: Event Logging Completeness**
    **Validates: Requirements 1.5, 7.1, 7.6**
    
    For any system event, a corresponding log entry must be created with:
    - Timestamp
    - Event type
    - Relevant context (session ID)
    """
    # Configure logging with JSON format
    configure_logging(level="INFO", session_id=session_id, json_format=True)
    
    # Create a logger
    logger = logging.getLogger("test_logger")
    
    # Capture log output
    import io
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JSONFormatter(session_id=session_id))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Create a log record with event type
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.event_type = event_type
    
    # Log the event
    handler.emit(record)
    
    # Parse the JSON log output
    log_output = log_stream.getvalue()
    log_entry = json.loads(log_output)
    
    # Verify all required fields are present
    assert "timestamp" in log_entry, "Log entry must have timestamp"
    assert "event_type" in log_entry, "Log entry must have event_type"
    assert "session_id" in log_entry, "Log entry must have session_id"
    assert "message" in log_entry, "Log entry must have message"
    
    # Verify field values
    assert log_entry["event_type"] == event_type
    assert log_entry["session_id"] == session_id
    
    # Verify timestamp format (ISO 8601)
    timestamp = log_entry["timestamp"]
    assert timestamp.endswith("Z"), "Timestamp must be in UTC (end with Z)"
    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise
    
    # Clean up
    logger.removeHandler(handler)


# Feature: livekit-agent-deployment, Property 6: Connection Pool Metrics Exposure
@given(
    size=st.integers(min_value=1, max_value=100),
    used_size=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
def test_property_6_connection_pool_metrics_exposure(size, used_size):
    """
    **Property 6: Connection Pool Metrics Exposure**
    **Validates: Requirements 7.3**
    
    For any state of the database connection pool, the system should be able
    to query and return accurate metrics about current usage, available
    connections, and usage percentage.
    """
    # Ensure used_size doesn't exceed size
    if used_size > size:
        used_size = size
    
    free_size = size - used_size
    
    # Create metrics collector
    collector = MetricsCollector()
    
    # Record connection pool stats
    collector.record_connection_pool_stats(
        size=size,
        free_size=free_size,
        used_size=used_size,
    )
    
    # Get metrics
    metrics = collector.get_connection_pool_metrics()
    
    # Verify all required fields are present
    assert "size" in metrics, "Metrics must include pool size"
    assert "free_size" in metrics, "Metrics must include free connections"
    assert "used_size" in metrics, "Metrics must include used connections"
    assert "usage_percent" in metrics, "Metrics must include usage percentage"
    assert "timestamp" in metrics, "Metrics must include timestamp"
    
    # Verify accuracy
    assert metrics["size"] == size
    assert metrics["free_size"] == free_size
    assert metrics["used_size"] == used_size
    
    # Verify usage percentage calculation
    expected_usage = (used_size / size * 100) if size > 0 else 0
    assert abs(metrics["usage_percent"] - expected_usage) < 0.01


# Feature: livekit-agent-deployment, Property 7: Latency Tracking
@given(
    operation=st.sampled_from(["stt", "llm", "tts", "end_to_end", "database_query"]),
    latency_ms=st.floats(min_value=0.1, max_value=5000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_property_7_latency_tracking(operation, latency_ms):
    """
    **Property 7: Latency Tracking**
    **Validates: Requirements 7.4**
    
    For any voice processing operation, the system should measure and record
    the latency with millisecond precision, making it available for monitoring.
    """
    # Create metrics collector
    collector = MetricsCollector()
    
    # Record latency
    collector.record_latency(operation, latency_ms)
    
    # Get latency metrics
    metrics = collector.get_latency_metrics(operation)
    
    # Verify operation is tracked
    assert operation in metrics, f"Operation {operation} must be tracked"
    
    # Verify latency was recorded
    latency_records = metrics[operation]
    assert len(latency_records) > 0, "At least one latency record must exist"
    
    # Verify the recorded value
    latest_record = latency_records[-1]
    assert "value" in latest_record, "Latency record must have value"
    assert "timestamp" in latest_record, "Latency record must have timestamp"
    
    # Verify precision (should match input within floating point tolerance)
    assert abs(latest_record["value"] - latency_ms) < 0.001
    
    # Verify timestamp format
    timestamp = latest_record["timestamp"]
    assert timestamp.endswith("Z"), "Timestamp must be in UTC"
    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise


# --- Unit Tests for Metrics Collector ---

def test_metrics_collector_singleton():
    """Test that get_metrics_collector returns the same instance."""
    collector1 = get_metrics_collector()
    collector2 = get_metrics_collector()
    assert collector1 is collector2


def test_metrics_collector_event_recording():
    """Test that events are recorded correctly."""
    collector = MetricsCollector()
    
    collector.record_event("test_event", {"detail": "test_detail"})
    
    metrics = collector.get_metrics()
    assert "test_event" in metrics["events"]
    assert len(metrics["events"]["test_event"]) == 1
    assert metrics["events"]["test_event"][0]["detail"] == "test_detail"


def test_metrics_collector_limits_history():
    """Test that metrics collector limits history size."""
    collector = MetricsCollector()
    
    # Record more than 100 latency measurements
    for i in range(150):
        collector.record_latency("test_op", float(i))
    
    metrics = collector.get_latency_metrics("test_op")
    assert len(metrics["test_op"]) == 100, "Should keep only last 100 measurements"


def test_json_formatter_includes_session_id():
    """Test that JSON formatter includes session ID."""
    session_id = "test-session-123"
    formatter = JSONFormatter(session_id=session_id)
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    formatted = formatter.format(record)
    log_entry = json.loads(formatted)
    
    assert log_entry["session_id"] == session_id


def test_json_formatter_sanitizes_secrets():
    """Test that JSON formatter sanitizes secrets in messages."""
    formatter = JSONFormatter()
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="API key: sk-1234567890abcdefghij",
        args=(),
        exc_info=None,
    )
    
    formatted = formatter.format(record)
    log_entry = json.loads(formatted)
    
    assert "sk-1234567890abcdefghij" not in log_entry["message"]
    assert "sk-***" in log_entry["message"]
