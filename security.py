"""
SupportAI-Env — Authentication & Security Module
User authentication, JWT tokens, rate limiting, and security utilities
"""

import hashlib
import hmac
import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from functools import wraps
import time
import uuid

# Simple JWT-like implementation (without external libraries for lite setup)

class SecurityManager:
    """Handle authentication, tokens, and security."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.active_tokens: Dict[str, Dict] = {}  # In-memory token store
    
    # ─── Password Hashing ──────────────────────────────────────────────────
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(8)
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${hash_obj.hex()}", salt
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt = stored_hash.split("$")[0]
            new_hash, _ = SecurityManager.hash_password(password, salt)
            return hmac.compare_digest(new_hash, stored_hash)
        except:
            return False
    
    # ─── Token Management ──────────────────────────────────────────────────
    
    def create_token(
        self,
        user_id: str,
        username: str,
        expires_in_hours: int = 24
    ) -> str:
        """Create a simple token (JWT-like but lightweight)."""
        payload = {
            "user_id": user_id,
            "username": username,
            "iat": int(time.time()),
            "exp": int(time.time()) + (expires_in_hours * 3600),
            "jti": secrets.token_urlsafe(16)  # Token ID (for revocation)
        }
        
        # Simple signing
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{payload_json}.{signature}"
        
        # Store for validation
        self.active_tokens[payload["jti"]] = {
            "user_id": user_id,
            "expires_at": payload["exp"]
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode token."""
        try:
            payload_json, signature = token.rsplit(".", 1)
            
            # Verify signature
            expected_sig = hmac.new(
                self.secret_key.encode(),
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_sig):
                return None
            
            payload = json.loads(payload_json)
            
            # Check expiration
            if payload.get("exp", 0) < int(time.time()):
                return None
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and jti not in self.active_tokens:
                return None
            
            return payload
        except:
            return None
    
    def revoke_token(self, token: str):
        """Revoke a token."""
        try:
            payload_json, _ = token.rsplit(".", 1)
            payload = json.loads(payload_json)
            jti = payload.get("jti")
            if jti and jti in self.active_tokens:
                del self.active_tokens[jti]
        except:
            pass
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens."""
        now = int(time.time())
        expired = [jti for jti, data in self.active_tokens.items()
                   if data["expires_at"] < now]
        for jti in expired:
            del self.active_tokens[jti]


# ─── Rate Limiter ──────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 100):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.buckets: Dict[str, Dict] = {}  # IP/User -> {tokens, last_refill}
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Dict]:
        """Check if request is allowed, return (allowed, info)."""
        now = time.time()
        
        if identifier not in self.buckets:
            self.buckets[identifier] = {
                "tokens": self.burst_size,
                "last_refill": now,
                "requests": 0
            }
        
        bucket = self.buckets[identifier]
        
        # Refill tokens based on time elapsed
        time_elapsed = now - bucket["last_refill"]
        tokens_to_add = (time_elapsed / 60.0) * self.requests_per_minute
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now
        bucket["requests"] += 1
        
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, {
                "remaining": int(bucket["tokens"]),
                "reset_in": int((1 / self.requests_per_minute) * 60)
            }
        
        return False, {
            "remaining": 0,
            "reset_in": int((1 / self.requests_per_minute) * 60)
        }
    
    def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Remove buckets for inactive clients."""
        now = time.time()
        old_keys = [k for k, v in self.buckets.items()
                    if (now - v["last_refill"]) > max_age_seconds]
        for k in old_keys:
            del self.buckets[k]


# ─── Input Validation ──────────────────────────────────────────────────────

class InputValidator:
    """Validate and sanitize user inputs."""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, Optional[str]]:
        """Validate username format."""
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(username) > 50:
            return False, "Username must be at most 50 characters"
        if not all(c.isalnum() or c in "-_" for c in username):
            return False, "Username can only contain letters, numbers, hyphens, and underscores"
        return True, None
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format."""
        if "@" not in email or "." not in email:
            return False, "Invalid email format"
        if len(email) > 254:
            return False, "Email is too long"
        return True, None
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """Validate password strength."""
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters"
        if len(password) > 128:
            return False, "Password is too long"
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and digits"
        return True, None
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 5000) -> str:
        """Sanitize and truncate text input."""
        if not isinstance(text, str):
            return ""
        text = text.strip()
        if len(text) > max_length:
            text = text[:max_length]
        # Remove dangerous characters
        dangerous = ["<", ">", "\"", "'"]
        for char in dangerous:
            text = text.replace(char, "")
        return text


# Global instances
security = SecurityManager()
rate_limiter = RateLimiter()
validator = InputValidator()
