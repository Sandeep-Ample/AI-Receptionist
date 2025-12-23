"""
Memory Service - Async PostgreSQL operations for user memory.

Handles:
- Connection pooling with asyncpg
- Fetching user memory before first greeting
- Saving conversation summaries after calls
- Graceful fallback when DB is unavailable
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger("receptionist-framework")

# Try to import asyncpg, graceful fallback if not available
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg not installed - memory features disabled")

from memory.models import CREATE_TABLE_SQL, FETCH_USER_SQL, UPSERT_USER_SQL, UPDATE_SUMMARY_SQL


class MemoryService:
    """
    Async PostgreSQL service for persistent user memory.
    
    Features:
    - Connection pooling for high performance
    - Auto-creates schema on first run
    - Graceful fallback when DB unavailable
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the memory service.
        
        Args:
            database_url: PostgreSQL connection string. 
                         If not provided, reads from DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self._pool: Optional["asyncpg.Pool"] = None
        self._initialized = False
        
        if not self.database_url:
            logger.info("No DATABASE_URL - memory features disabled (no-memory mode)")
        elif not ASYNCPG_AVAILABLE:
            logger.warning("asyncpg not available - memory features disabled")
    
    @property
    def is_enabled(self) -> bool:
        """Check if memory features are enabled."""
        return bool(self.database_url and ASYNCPG_AVAILABLE)
    
    async def initialize(self) -> bool:
        """
        Initialize the connection pool and create schema if needed.
        
        Returns:
            True if initialization succeeded, False otherwise.
        """
        if self._initialized:
            return True
        
        if not self.is_enabled:
            return False
        
        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=10.0
            )
            
            # Create schema if it doesn't exist
            async with self._pool.acquire() as conn:
                await conn.execute(CREATE_TABLE_SQL)
            
            self._initialized = True
            logger.info("Memory service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            self._pool = None
            return False
    
    async def fetch_user(self, caller_id: str) -> Optional[dict]:
        """
        Fetch user memory from PostgreSQL.
        
        Args:
            caller_id: The participant identity (phone number or user ID)
        
        Returns:
            Dict with user memory or None if not found/disabled.
            Keys: phone_number, name, last_summary, last_call, call_count, metadata
        """
        if not self._initialized or not self._pool:
            if self.is_enabled:
                # Try to initialize on first use
                await self.initialize()
            if not self._pool:
                return None
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(FETCH_USER_SQL, caller_id)
                
                if row:
                    result = dict(row)
                    logger.info(f"Found memory for caller: {caller_id} (name: {result.get('name')})")
                    return result
                else:
                    logger.info(f"No memory found for caller: {caller_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching user memory: {e}")
            return None
    
    async def save_user(
        self, 
        caller_id: str, 
        name: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Save or update user memory.
        
        Args:
            caller_id: The participant identity
            name: User's name (optional, won't overwrite if None)
            summary: Conversation summary
            metadata: Additional JSON metadata
        
        Returns:
            True if save succeeded, False otherwise.
        """
        if not self._pool:
            return False
        
        try:
            metadata_json = json.dumps(metadata or {})
            
            async with self._pool.acquire() as conn:
                await conn.execute(
                    UPSERT_USER_SQL,
                    caller_id,
                    name,
                    summary,
                    metadata_json
                )
            
            logger.info(f"Saved memory for caller: {caller_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving user memory: {e}")
            return False
    
    async def update_summary(self, caller_id: str, summary: str) -> bool:
        """
        Update only the conversation summary for a user.
        
        This is used for async summarization after call ends.
        
        Args:
            caller_id: The participant identity
            summary: New conversation summary
        
        Returns:
            True if update succeeded, False otherwise.
        """
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(UPDATE_SUMMARY_SQL, caller_id, summary)
            
            logger.info(f"Updated summary for caller: {caller_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating summary: {e}")
            return False
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("Memory service closed")


# Global singleton instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create the global MemoryService instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
