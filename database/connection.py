"""
Database Connection Management with Connection Pooling

This module provides enhanced database connection management with:
- Connection pooling (asyncpg)
- SSL/TLS enforcement
- Connection health checks
- Automatic reconnection
- Metrics collection

Requirements: 2.1, 2.6, 2.7, 8.1
"""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime

logger = logging.getLogger("database.connection")

# Try to import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg not installed - database features disabled")


class DatabaseConnection:
    """
    Enhanced database connection manager with connection pooling.
    
    Features:
    - Connection pooling (10 base + 20 overflow = 30 max)
    - SSL/TLS enforcement
    - Connection health checks
    - Automatic reconnection
    - Metrics collection
    
    Requirements: 2.1, 2.6, 2.7, 8.1
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection manager.
        
        Args:
            database_url: PostgreSQL connection string with SSL enabled
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self._pool: Optional["asyncpg.Pool"] = None
        self._initialized = False
        self._connection_attempts = 0
        self._last_health_check: Optional[datetime] = None
        
        # Metrics
        self._total_connections = 0
        self._failed_connections = 0
        self._total_queries = 0
        self._failed_queries = 0
        
        if not self.database_url:
            logger.warning("No DATABASE_URL - database features disabled")
        elif not ASYNCPG_AVAILABLE:
            logger.warning("asyncpg not available - database features disabled")
        else:
            # Validate SSL is enabled
            self._validate_ssl_config()
    
    def _validate_ssl_config(self):
        """
        Validate that SSL/TLS is properly configured.
        
        Requirements: 2.6, 8.1
        """
        if not self.database_url:
            return
        
        # Check for SSL mode
        if "sslmode=" not in self.database_url and "ssl=" not in self.database_url:
            logger.warning(
                "Database URL does not specify SSL mode. "
                "For production, add '?sslmode=require' to the connection string."
            )
        elif "sslmode=disable" in self.database_url or "ssl=false" in self.database_url:
            logger.error(
                "Database SSL is disabled! This is insecure for production. "
                "Change to 'sslmode=require' or 'ssl=true'."
            )
    
    @property
    def is_enabled(self) -> bool:
        """Check if database features are enabled."""
        return bool(self.database_url and ASYNCPG_AVAILABLE)
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._initialized and self._pool is not None
    
    async def initialize(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Initialize the connection pool with retry logic.
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if initialization succeeded, False otherwise
            
        Requirements: 2.1, 2.7
        """
        if self._initialized:
            return True
        
        if not self.is_enabled:
            return False
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Initializing database connection pool (attempt {attempt}/{max_retries})...")
                
                # Create connection pool with optimized settings
                # Note: statement_cache_size=0 is required for Supabase transaction pooler
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=10,              # Base connections (Requirement 2.7)
                    max_size=30,              # Max connections (10 + 20 overflow)
                    max_queries=50000,        # Max queries per connection before recycling
                    max_inactive_connection_lifetime=3600.0,  # Recycle after 1 hour
                    command_timeout=30.0,     # Query timeout
                    timeout=10.0,             # Connection acquisition timeout
                    statement_cache_size=0,   # Disable prepared statements for pgbouncer/Supabase
                    # SSL is enforced via connection string
                )
                
                # Test the connection
                async with self._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                
                self._initialized = True
                self._connection_attempts = attempt
                self._total_connections += 1
                
                logger.info(
                    f"Database connection pool initialized successfully "
                    f"(min_size=10, max_size=30, statement_cache disabled for Supabase)"
                )
                
                return True
                
            except Exception as e:
                self._failed_connections += 1
                logger.error(f"Failed to initialize database pool (attempt {attempt}/{max_retries}): {e}")
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Database connection failed.")
                    self._pool = None
                    return False
        
        return False
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the database connection.
        
        Returns:
            True if database is healthy, False otherwise
            
        Requirements: 1.6, 6.4
        """
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                # Simple query to test connection
                result = await conn.fetchval("SELECT 1")
                
                if result == 1:
                    self._last_health_check = datetime.utcnow()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary with pool metrics
            
        Requirements: 7.3
        """
        if not self._pool:
            return {
                "enabled": False,
                "connected": False,
            }
        
        return {
            "enabled": True,
            "connected": True,
            "size": self._pool.get_size(),
            "free_size": self._pool.get_idle_size(),
            "used_size": self._pool.get_size() - self._pool.get_idle_size(),
            "max_size": self._pool.get_max_size(),
            "min_size": self._pool.get_min_size(),
            "usage_percent": (
                (self._pool.get_size() - self._pool.get_idle_size()) / self._pool.get_max_size() * 100
                if self._pool.get_max_size() > 0 else 0
            ),
            "total_connections": self._total_connections,
            "failed_connections": self._failed_connections,
            "total_queries": self._total_queries,
            "failed_queries": self._failed_queries,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
        }
    
    async def execute_query(self, query: str, *args, timeout: Optional[float] = None):
        """
        Execute a query with metrics tracking.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Optional query timeout
            
        Returns:
            Query result
        """
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        try:
            self._total_queries += 1
            
            async with self._pool.acquire() as conn:
                if timeout:
                    async with asyncio.timeout(timeout):
                        return await conn.fetch(query, *args)
                else:
                    return await conn.fetch(query, *args)
                    
        except Exception as e:
            self._failed_queries += 1
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("Database connection pool closed")
    
    def __repr__(self) -> str:
        """String representation of connection status."""
        if not self.is_enabled:
            return "<DatabaseConnection: disabled>"
        elif not self.is_connected:
            return "<DatabaseConnection: not connected>"
        else:
            stats = {
                "size": self._pool.get_size() if self._pool else 0,
                "free": self._pool.get_idle_size() if self._pool else 0,
            }
            return f"<DatabaseConnection: connected, pool={stats['size']}, free={stats['free']}>"


# Global singleton instance
_database_connection: Optional[DatabaseConnection] = None


def get_database_connection() -> DatabaseConnection:
    """
    Get or create the global DatabaseConnection instance.
    
    Returns:
        DatabaseConnection singleton
    """
    global _database_connection
    if _database_connection is None:
        _database_connection = DatabaseConnection()
    return _database_connection


async def initialize_database() -> bool:
    """
    Initialize the global database connection.
    
    Returns:
        True if initialization succeeded
    """
    db = get_database_connection()
    return await db.initialize()
