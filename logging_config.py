"""
Logging Configuration Module

Provides structured JSON logging with:
- Environment-based log levels
- Context fields (timestamp, session_id, event_type)
- Secret sanitization
- Metrics collection
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

# Secret patterns to sanitize
SECRET_PATTERNS = [
    (re.compile(r'(sk-[a-zA-Z0-9]{20,})'), 'sk-***'),  # OpenAI keys
    (re.compile(r'(Bearer\s+[a-zA-Z0-9\-._~+/]+=*)'), 'Bearer ***'),  # Bearer tokens
    (re.compile(r'(api[_-]?key["\s:=]+)([a-zA-Z0-9\-._~+/]+)', re.IGNORECASE), r'\1***'),  # API keys
    (re.compile(r'(password["\s:=]+)([^\s"]+)', re.IGNORECASE), r'\1***'),  # Passwords
    (re.compile(r'(token["\s:=]+)([a-zA-Z0-9\-._~+/]+)', re.IGNORECASE), r'\1***'),  # Tokens
]


def sanitize_message(message: str) -> str:
    """
    Remove secrets from log messages.
    
    Args:
        message: The log message to sanitize
        
    Returns:
        Sanitized message with secrets replaced
    """
    sanitized = message
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON with structured fields.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.session_id = session_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_message(record.getMessage()),
        }
        
        # Add session ID if available
        if self.session_id:
            log_entry["session_id"] = self.session_id
        
        # Add event type if present
        if hasattr(record, "event_type"):
            log_entry["event_type"] = record.event_type
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


def configure_logging(
    level: Optional[str] = None,
    session_id: Optional[str] = None,
    json_format: bool = True
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If not provided, reads from LOG_LEVEL env var (default: INFO)
        session_id: Optional session ID to include in all logs
        json_format: If True, use JSON formatting; otherwise use standard format
    """
    # Determine log level
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    log_level = getattr(logging, level, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter(session_id=session_id)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


class MetricsCollector:
    """
    Collects and exposes metrics for monitoring.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "connection_pool": {},
            "latency": {},
            "events": {},
        }
    
    def record_connection_pool_stats(
        self,
        size: int,
        free_size: int,
        used_size: int
    ) -> None:
        """Record connection pool statistics."""
        self._metrics["connection_pool"] = {
            "size": size,
            "free_size": free_size,
            "used_size": used_size,
            "usage_percent": (used_size / size * 100) if size > 0 else 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    def record_latency(
        self,
        operation: str,
        latency_ms: float
    ) -> None:
        """Record operation latency in milliseconds."""
        if operation not in self._metrics["latency"]:
            self._metrics["latency"][operation] = []
        
        self._metrics["latency"][operation].append({
            "value": latency_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        
        # Keep only last 100 measurements per operation
        if len(self._metrics["latency"][operation]) > 100:
            self._metrics["latency"][operation] = self._metrics["latency"][operation][-100:]
    
    def record_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an event occurrence."""
        if event_type not in self._metrics["events"]:
            self._metrics["events"][event_type] = []
        
        event_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if details:
            event_entry.update(details)
        
        self._metrics["events"][event_type].append(event_entry)
        
        # Keep only last 50 events per type
        if len(self._metrics["events"][event_type]) > 50:
            self._metrics["events"][event_type] = self._metrics["events"][event_type][-50:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self._metrics.copy()
    
    def get_connection_pool_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics."""
        return self._metrics["connection_pool"].copy()
    
    def get_latency_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get latency metrics.
        
        Args:
            operation: If provided, return metrics for specific operation only
        """
        if operation:
            return {operation: self._metrics["latency"].get(operation, [])}
        return self._metrics["latency"].copy()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global MetricsCollector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
