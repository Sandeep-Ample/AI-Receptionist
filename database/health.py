"""
Database Health Check Module

Provides health check functionality for database connectivity.

Requirements: 1.6, 6.4
"""

import logging
from typing import Dict, Any
from datetime import datetime

from .connection import get_database_connection

logger = logging.getLogger("database.health")


async def check_database_health() -> Dict[str, Any]:
    """
    Perform comprehensive database health check.
    
    Returns:
        Dictionary with health check results:
        - healthy: bool - Overall health status
        - connected: bool - Connection status
        - pool_stats: dict - Connection pool statistics
        - latency_ms: float - Query latency in milliseconds
        - timestamp: str - Check timestamp
        
    Requirements: 1.6, 6.4
    """
    db = get_database_connection()
    
    result = {
        "healthy": False,
        "connected": False,
        "pool_stats": {},
        "latency_ms": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check if database is enabled
    if not db.is_enabled:
        result["error"] = "Database not enabled (missing DATABASE_URL or asyncpg)"
        return result
    
    # Check if connected
    if not db.is_connected:
        result["error"] = "Database not connected"
        return result
    
    result["connected"] = True
    
    # Perform health check with latency measurement
    try:
        start_time = datetime.utcnow()
        healthy = await db.health_check()
        end_time = datetime.utcnow()
        
        latency = (end_time - start_time).total_seconds() * 1000  # Convert to ms
        
        result["healthy"] = healthy
        result["latency_ms"] = round(latency, 2)
        
        # Get pool statistics
        result["pool_stats"] = await db.get_pool_stats()
        
        # Check for warnings
        if result["pool_stats"].get("usage_percent", 0) > 80:
            result["warning"] = "Connection pool usage above 80%"
        
        if latency > 100:
            result["warning"] = f"High database latency: {latency:.2f}ms"
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        result["healthy"] = False
        result["error"] = str(e)
    
    return result


async def check_database_connectivity() -> bool:
    """
    Simple connectivity check (returns True/False).
    
    Returns:
        True if database is healthy, False otherwise
        
    Requirements: 1.6
    """
    health = await check_database_health()
    return health.get("healthy", False)


async def get_database_metrics() -> Dict[str, Any]:
    """
    Get database metrics for monitoring.
    
    Returns:
        Dictionary with database metrics
        
    Requirements: 7.3
    """
    db = get_database_connection()
    
    if not db.is_enabled or not db.is_connected:
        return {
            "enabled": db.is_enabled,
            "connected": db.is_connected,
        }
    
    return await db.get_pool_stats()
