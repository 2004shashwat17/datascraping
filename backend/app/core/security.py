"""
Security utilities for authentication, authorization, and data protection.
Implements JWT token management and password hashing with Azure integration.
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
import secrets
import hashlib
import logging

from app.core.config import get_settings
from app.models.mongo_models import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


class Token(BaseModel):
    """JWT Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """JWT Token data model"""
    username: Optional[str] = None
    scopes: list[str] = []


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security_settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.security_settings.secret_key,
            algorithm=settings.security_settings.algorithm
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.security_settings.secret_key,
            algorithms=[settings.security_settings.algorithm]
        )
        username: str = payload.get("sub")
        scopes: list = payload.get("scopes", [])
        
        if username is None:
            return None
            
        return TokenData(username=username, scopes=scopes)
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_password() -> str:
    """
    Generate a secure random password
    
    Returns:
        Random password string
    """
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """
    Generate a secure API key
    
    Returns:
        API key string
    """
    return f"osint_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage
    
    Args:
        api_key: API key to hash
        
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_api_key: str) -> bool:
    """
    Verify API key against hash
    
    Args:
        api_key: API key to verify
        hashed_api_key: Hashed API key
        
    Returns:
        True if API key matches, False otherwise
    """
    return hash_api_key(api_key) == hashed_api_key


def sanitize_input(input_string: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks
    
    Args:
        input_string: Input to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized input string
    """
    if not input_string:
        return ""
    
    # Remove dangerous characters
    sanitized = input_string.replace("<", "&lt;").replace(">", "&gt;")
    sanitized = sanitized.replace("&", "&amp;").replace('"', "&quot;")
    sanitized = sanitized.replace("'", "&#x27;").replace("/", "&#x2F;")
    
    # Truncate to max length
    return sanitized[:max_length]


def validate_social_media_url(url: str) -> bool:
    """
    Validate social media URLs for security
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is safe, False otherwise
    """
    if not url:
        return False
    
    # Allowed domains for social media platforms
    allowed_domains = [
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "youtube.com",
        "reddit.com",
        "tiktok.com",
        "snapchat.com"
    ]
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Check if domain is in allowed list
        domain = parsed.netloc.lower()
        for allowed in allowed_domains:
            if domain.endswith(allowed):
                return True
        
        return False
    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return False


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging and display
    
    Args:
        data: Sensitive data to mask
        visible_chars: Number of characters to show
        
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""
    
    return data[:visible_chars] + "*" * (len(data) - visible_chars)


def generate_correlation_id() -> str:
    """
    Generate correlation ID for request tracking
    
    Returns:
        Unique correlation ID
    """
    return secrets.token_hex(16)


class SecurityHeaders:
    """Security headers for HTTP responses"""
    
    @staticmethod
    def get_headers() -> dict:
        """Get recommended security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    Log security-related events for monitoring
    
    Args:
        event_type: Type of security event
        user_id: User ID if applicable
        ip_address: Client IP address
        details: Additional event details
    """
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "ip_address": ip_address,
        "details": details or {}
    }
    
    logger.info(f"Security event: {log_data}")
    
    # TODO: Send to Azure Security Center or external SIEM
    # This could be extended to send alerts to Azure Monitor or other security tools


async def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username."""
    try:
        user = await User.find_one(User.username == username)
        return user
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        # Fallback to in-memory storage if needed
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user