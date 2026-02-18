"""
OTP Service - One-Time Password Generation and Verification

Handles:
- 6-digit OTP generation
- Secure hashing for storage
- Time-based expiry (5 minutes)
- Rate limiting (max 3 attempts)
"""

import secrets
import string
import hashlib
import time
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger("otp_service")


class OTPService:
    """
    OTP service for email verification.
    
    Features:
    - 6-digit numeric OTP
    - SHA256 hashing for storage
    - 5-minute expiry
    - 3 attempt limit
    - In-memory storage (use Redis for production)
    """
    
    def __init__(self, expiry_seconds: int = 300, max_attempts: int = 3):
        """
        Initialize OTP service.
        
        Args:
            expiry_seconds: OTP validity duration (default: 5 minutes)
            max_attempts: Maximum verification attempts (default: 3)
        """
        self.expiry_seconds = expiry_seconds
        self.max_attempts = max_attempts
        self.otp_store: Dict[str, dict] = {}
    
    def _hash_otp(self, otp: str) -> str:
        """Hash OTP using SHA256"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    def generate_otp(self, email: str) -> str:
        """
        Generate a 6-digit OTP for the given email.
        
        Args:
            email: User's email address
        
        Returns:
            The plain OTP (6 digits) - send this to user
        """
        # Generate 6-digit OTP
        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        # Hash for storage
        hashed_otp = self._hash_otp(otp)
        
        # Store with metadata
        self.otp_store[email] = {
            "otp": hashed_otp,
            "created_at": time.time(),
            "attempts": 0,
            "otp_plain": otp  # For development/testing only - remove in production
        }
        
        logger.info(f"Generated OTP for {email}")
        
        return otp
    
    def verify_otp(self, email: str, user_otp: str) -> bool:
        """
        Verify the OTP entered by user.
        
        Args:
            email: User's email address
            user_otp: OTP entered by user
        
        Returns:
            True if OTP is valid, False otherwise
        """
        if email not in self.otp_store:
            logger.warning(f"No OTP found for {email}")
            return False
        
        stored = self.otp_store[email]
        
        # Check if OTP has expired
        if time.time() - stored["created_at"] > self.expiry_seconds:
            logger.warning(f"OTP expired for {email}")
            del self.otp_store[email]
            return False
        
        # Check if max attempts exceeded
        if stored["attempts"] >= self.max_attempts:
            logger.warning(f"Max attempts exceeded for {email}")
            del self.otp_store[email]
            return False
        
        # Hash the user input and compare
        hashed_input = self._hash_otp(user_otp)
        
        if hashed_input == stored["otp"]:
            # Successful verification - remove OTP
            del self.otp_store[email]
            logger.info(f"OTP verified successfully for {email}")
            return True
        
        # Failed attempt
        stored["attempts"] += 1
        logger.warning(f"Invalid OTP attempt for {email}: {stored['attempts']}/{self.max_attempts}")
        return False
    
    def resend_otp(self, email: str) -> Optional[str]:
        """
        Resend a new OTP (generates new one).
        
        Args:
            email: User's email address
        
        Returns:
            New OTP or None if rate limited
        """
        # Check if there's an existing OTP
        if email in self.otp_store:
            stored = self.otp_store[email]
            time_since_creation = time.time() - stored["created_at"]
            
            # Rate limit: don't allow more than 1 OTP per minute
            if time_since_creation < 60:
                logger.warning(f"Rate limited OTP resend for {email}")
                return None
        
        return self.generate_otp(email)
    
    def has_otp(self, email: str) -> bool:
        """Check if there's a pending OTP for the email"""
        return email in self.otp_store
    
    def get_remaining_time(self, email: str) -> int:
        """Get remaining seconds before OTP expires"""
        if email not in self.otp_store:
            return 0
        
        stored = self.otp_store[email]
        elapsed = time.time() - stored["created_at"]
        remaining = self.expiry_seconds - int(elapsed)
        return max(0, remaining)
    
    def clear_otp(self, email: str):
        """Manually clear OTP for an email"""
        if email in self.otp_store:
            del self.otp_store[email]
            logger.info(f"Cleared OTP for {email}")
    
    # For development/testing only - remove in production
    def get_otp_for_testing(self, email: str) -> Optional[str]:
        """Get plain OTP for testing purposes"""
        if email in self.otp_store:
            return self.otp_store[email].get("otp_plain")
        return None


# Global singleton instance
_otp_service: Optional[OTPService] = None


def get_otp_service() -> OTPService:
    """Get or create the global OTPService instance."""
    global _otp_service
    if _otp_service is None:
        _otp_service = OTPService()
    return _otp_service
