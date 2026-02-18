"""
Memory Service - Async PostgreSQL operations for user memory.

Handles:
- Connection pooling with asyncpg
- Fetching user memory before first greeting
- Saving conversation summaries after calls
- Graceful fallback when DB is unavailable

This service now uses the enhanced DatabaseConnection for better
connection management and monitoring.
"""

import json
import logging
import os
from typing import Optional

from database import get_database_connection

logger = logging.getLogger("receptionist-framework")

# Try to import asyncpg, graceful fallback if not available
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg not installed - memory features disabled")

from memory.models import (
    CREATE_TABLE_SQL, 
    FETCH_USER_SQL, 
    FETCH_USER_BY_EMAIL_SQL,
    UPSERT_USER_SQL, 
    UPSERT_USER_BY_EMAIL_SQL,
    UPDATE_SUMMARY_SQL,
    UPDATE_APPROVAL_SQL
)


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
        # Use the enhanced database connection
        self.db_connection = get_database_connection()
        self._initialized = False
        
        if not self.db_connection.is_enabled:
            logger.info("No DATABASE_URL - memory features disabled (no-memory mode)")
    
    @property
    def _pool(self):
        """Access the connection pool from DatabaseConnection."""
        return self.db_connection._pool if self.db_connection else None
    
    @property
    def is_enabled(self) -> bool:
        """Check if memory features are enabled."""
        return self.db_connection.is_enabled if self.db_connection else False
    
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
            # Initialize the database connection
            if not await self.db_connection.initialize():
                return False
            
            # Create schema if it doesn't exist
            async with self._pool.acquire() as conn:
                await conn.execute(CREATE_TABLE_SQL)
            
            self._initialized = True
            logger.info("Memory service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            return False
    
    async def fetch_user(self, caller_id: str) -> Optional[dict]:
        """
        Fetch user memory from PostgreSQL.
        
        Args:
            caller_id: The participant identity (email or phone number)
        
        Returns:
            Dict with user memory or None if not found/disabled.
            Keys: phone_number, email, name, last_summary, last_call, call_count, is_approved, metadata
        """
        if not self._initialized or not self._pool:
            if self.is_enabled:
                # Try to initialize on first use
                await self.initialize()
            if not self._pool:
                return None
        
        try:
            async with self._pool.acquire() as conn:
                # Try email first, then phone number
                row = await conn.fetchrow(FETCH_USER_BY_EMAIL_SQL, caller_id)
                if not row:
                    row = await conn.fetchrow(FETCH_USER_SQL, caller_id)
                
                if row:
                    result = dict(row)
                    logger.info(f"Found memory for caller: {caller_id} (name: {result.get('name')}, approved: {result.get('is_approved')})")
                    return result
                else:
                    logger.info(f"No memory found for caller: {caller_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching user memory: {e}")
            return None
    
    async def fetch_user_by_email(self, email: str) -> Optional[dict]:
        """
        Fetch user memory by email address.
        
        Args:
            email: User's email address
        
        Returns:
            Dict with user memory or None if not found/disabled.
        """
        if not self._initialized or not self._pool:
            if self.is_enabled:
                await self.initialize()
            if not self._pool:
                return None
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(FETCH_USER_BY_EMAIL_SQL, email)
                
                if row:
                    result = dict(row)
                    logger.info(f"Found user by email: {email} (name: {result.get('name')}, approved: {result.get('is_approved')})")
                    return result
                else:
                    logger.info(f"No user found with email: {email}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None
    
    async def save_user(
        self, 
        caller_id: str, 
        email: Optional[str] = None,
        name: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Save or update user memory.
        
        Args:
            caller_id: The participant identity
            email: User's email address (preferred)
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
            
            # Use email-based upsert if email is provided
            if email:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        UPSERT_USER_BY_EMAIL_SQL,
                        email,
                        name,
                        False  # is_approved - default to false for new users
                    )
                logger.info(f"Saved memory for email: {email}")
            else:
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
    
    async def create_user_with_approval(
        self,
        email: str,
        name: Optional[str] = None,
        password_hash: Optional[str] = None,
        is_approved: bool = False
    ) -> bool:
        """
        Create a new user with optional approval status.
        
        Args:
            email: User's email address (required, used as unique identifier)
            name: User's name
            password_hash: Hashed password
            is_approved: Whether user is approved to use the system
        
        Returns:
            True if user created successfully, False if email already exists
        """
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_memory (email, name, password_hash, is_approved, approved_at)
                    VALUES ($1, $2, $3, $4, CASE WHEN $4 = TRUE THEN NOW() ELSE NULL END)
                    ON CONFLICT (email) 
                    DO NOTHING
                    """,
                    email,
                    name,
                    password_hash,
                    is_approved
                )
                
            logger.info(f"Created user: {email}, approved: {is_approved}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def check_approval_status(self, email: str) -> Optional[dict]:
        """
        Check if a user is approved to use the system.
        
        Args:
            email: User's email address
        
        Returns:
            Dict with is_approved status and user info, or None if not found
        """
        if not self._pool:
            return None
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT email, name, is_approved, approved_at FROM user_memory WHERE email = $1",
                    email
                )
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error checking approval status: {e}")
            return None
    
    async def update_approval_status(self, email: str, is_approved: bool) -> bool:
        """
        Update user's approval status.
        
        Args:
            email: User's email address
            is_approved: New approval status
        
        Returns:
            True if update succeeded, False otherwise
        """
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    UPDATE_APPROVAL_SQL,
                    email,
                    is_approved
                )
            
            logger.info(f"Updated approval status for {email}: {is_approved}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating approval status: {e}")
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
        if self.db_connection:
            await self.db_connection.close()
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
