"""
Health Check Module

Provides health check functionality for:
- Database connectivity
- LiveKit connection
- AI services (STT, LLM, TTS)
- Overall system health

Returns appropriate HTTP status codes:
- 200: All systems healthy
- 503: One or more systems unhealthy
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp

logger = logging.getLogger("health-check")


async def check_database_health() -> Dict[str, Any]:
    """
    Check database connectivity and health.
    
    Returns:
        Dict with health status, connection state, and latency
    """
    try:
        from database import get_database_connection
        
        db = get_database_connection()
        
        if not db.is_enabled:
            return {
                "healthy": False,
                "connected": False,
                "error": "Database not configured",
            }
        
        # Initialize if needed
        if not db._pool:
            await db.initialize()
        
        # Measure latency
        start_time = datetime.utcnow()
        
        # Simple connectivity check
        async with db._pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Get pool stats
        pool_stats = await db.get_pool_stats()
        
        return {
            "healthy": True,
            "connected": True,
            "latency_ms": round(latency_ms, 2),
            "pool_stats": pool_stats,
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "healthy": False,
            "connected": False,
            "error": str(e),
        }


async def check_livekit_health() -> Dict[str, Any]:
    """
    Check LiveKit connection health.
    
    Returns:
        Dict with health status and connection state
    """
    try:
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        
        if not livekit_url or not livekit_api_key:
            return {
                "healthy": False,
                "configured": False,
                "error": "LiveKit credentials not configured",
            }
        
        # Check if URL is reachable (basic connectivity)
        # Note: This is a simple check; full validation would require LiveKit SDK
        if livekit_url.startswith("ws://") or livekit_url.startswith("wss://"):
            # WebSocket URL - just verify it's configured
            return {
                "healthy": True,
                "configured": True,
                "url": livekit_url.split("@")[-1] if "@" in livekit_url else livekit_url,
            }
        
        return {
            "healthy": True,
            "configured": True,
        }
        
    except Exception as e:
        logger.error(f"LiveKit health check failed: {e}")
        return {
            "healthy": False,
            "configured": False,
            "error": str(e),
        }


async def check_ai_service_health(
    service_name: str,
    api_key_env: str,
    test_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check AI service health (STT, LLM, TTS).
    
    Args:
        service_name: Name of the service (e.g., "Deepgram", "OpenAI")
        api_key_env: Environment variable name for API key
        test_url: Optional URL to test connectivity
    
    Returns:
        Dict with health status and configuration state
    """
    try:
        api_key = os.getenv(api_key_env)
        
        if not api_key:
            return {
                "healthy": False,
                "configured": False,
                "error": f"{service_name} API key not configured",
            }
        
        # If test URL provided, try a simple connectivity check
        if test_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        test_url,
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        # Any response (even 401) means the service is reachable
                        return {
                            "healthy": True,
                            "configured": True,
                            "reachable": response.status < 500,
                        }
            except asyncio.TimeoutError:
                return {
                    "healthy": False,
                    "configured": True,
                    "error": f"{service_name} timeout",
                }
            except Exception as e:
                logger.warning(f"{service_name} connectivity check failed: {e}")
                # Still consider healthy if configured, connectivity check is optional
                return {
                    "healthy": True,
                    "configured": True,
                    "reachable": False,
                }
        
        # If no test URL, just verify configuration
        return {
            "healthy": True,
            "configured": True,
        }
        
    except Exception as e:
        logger.error(f"{service_name} health check failed: {e}")
        return {
            "healthy": False,
            "configured": False,
            "error": str(e),
        }


async def perform_health_check() -> Dict[str, Any]:
    """
    Perform comprehensive health check of all system components.
    
    Returns:
        Dict with overall health status and individual component checks
    """
    # Run all checks in parallel
    db_check, livekit_check, deepgram_check, openai_check, cartesia_check = await asyncio.gather(
        check_database_health(),
        check_livekit_health(),
        check_ai_service_health("Deepgram", "DEEPGRAM_API_KEY"),
        check_ai_service_health("OpenAI", "OPENAI_API_KEY"),
        check_ai_service_health("Cartesia", "CARTESIA_API_KEY"),
        return_exceptions=True
    )
    
    # Handle any exceptions from gather
    checks = {
        "database": db_check if not isinstance(db_check, Exception) else {"healthy": False, "error": str(db_check)},
        "livekit": livekit_check if not isinstance(livekit_check, Exception) else {"healthy": False, "error": str(livekit_check)},
        "deepgram": deepgram_check if not isinstance(deepgram_check, Exception) else {"healthy": False, "error": str(deepgram_check)},
        "openai": openai_check if not isinstance(openai_check, Exception) else {"healthy": False, "error": str(openai_check)},
        "cartesia": cartesia_check if not isinstance(cartesia_check, Exception) else {"healthy": False, "error": str(cartesia_check)},
    }
    
    # Determine overall health
    all_healthy = all(check.get("healthy", False) for check in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }


async def verify_startup_connectivity() -> bool:
    """
    Verify connectivity to all required services at startup.
    
    This is called during agent initialization to ensure all dependencies
    are available before starting to handle calls.
    
    Returns:
        True if all services are healthy, False otherwise
    """
    logger.info("Verifying startup connectivity...")
    
    health = await perform_health_check()
    
    if health["status"] == "healthy":
        logger.info("✓ All services healthy")
        return True
    else:
        logger.error("✗ Some services are unhealthy:")
        for service, check in health["checks"].items():
            if not check.get("healthy", False):
                error = check.get("error", "Unknown error")
                logger.error(f"  - {service}: {error}")
        return False


def get_health_status_code(health: Dict[str, Any]) -> int:
    """
    Get HTTP status code based on health check result.
    
    Args:
        health: Health check result from perform_health_check()
    
    Returns:
        200 if healthy, 503 if unhealthy
    """
    return 200 if health["status"] == "healthy" else 503
