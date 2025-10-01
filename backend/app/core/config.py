"""
Core configuration settings for the OSINT platform backend.
Uses Pydantic Settings for environment variable management.
"""

from functools import lru_cache
from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseModel):
    """Database connection settings"""
    url: str = Field(..., description="MongoDB database URL")
    echo: bool = Field(False, description="Enable database query logging")
    pool_size: int = Field(10, description="Database connection pool size")
    max_overflow: int = Field(20, description="Maximum connection overflow")


class SecuritySettings(BaseModel):
    """Security and authentication settings"""
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="JWT token expiration time")
    
    
# Azure settings removed - using simplified MongoDB-only stack


class SocialMediaSettings(BaseModel):
    """Social media API configuration"""
    facebook_app_id: Optional[str] = Field(None, description="Facebook App ID")
    facebook_app_secret: Optional[str] = Field(None, description="Facebook App Secret")
    twitter_bearer_token: Optional[str] = Field(None, description="Twitter API Bearer Token")
    twitter_api_key: Optional[str] = Field(None, description="Twitter API Key")
    twitter_api_secret: Optional[str] = Field(None, description="Twitter API Secret")
    instagram_client_id: Optional[str] = Field(None, description="Instagram Client ID")
    instagram_client_secret: Optional[str] = Field(None, description="Instagram Client Secret")


class ThreatDetectionSettings(BaseModel):
    """Threat detection and analysis configuration"""
    keyword_threshold: float = Field(0.7, description="Keyword matching threshold")
    sentiment_threshold: float = Field(-0.5, description="Negative sentiment threshold")
    enable_ml_detection: bool = Field(True, description="Enable ML-based threat detection")
    threat_keywords: List[str] = Field(
        default=[
            "bomb", "attack", "terror", "violence", "weapon", "threat",
            "kill", "murder", "assassinate", "destroy", "explosive"
        ],
        description="List of threat-related keywords"
    )


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application settings
    app_name: str = Field("OSINT Data Collection Platform", description="Application name")
    debug: bool = Field(False, description="Debug mode")
    version: str = Field("1.0.0", description="Application version")
    
    # Server settings
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    
    # Database settings  
    database_url: str = Field(..., description="MongoDB connection URL")
    mongodb_url: Optional[str] = Field(None, description="MongoDB connection URL (alias)")
    db_name: str = Field("dataplatform", description="Database name")
    
    # Security settings
    SECRET_KEY: str = Field("dev-secret-key-change-in-production", description="JWT secret key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="JWT token expiration time in minutes")
    
    # Apify API settings
    apify_api_token: str = Field("", description="Apify API token for web scraping")
    
    # TwitterApiIO settings
    twitter_api_io_key: str = Field("", description="TwitterApiIO API key for Twitter data collection")
    
    # Additional service configurations can be added here as needed
    
    # Logging settings
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # API settings
    api_prefix: str = Field("/api/v1", description="API prefix")
    docs_url: str = Field("/docs", description="API documentation URL")
    redoc_url: str = Field("/redoc", description="ReDoc documentation URL")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "https://localhost:3000"],
        description="Allowed CORS origins"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    allowed_headers: List[str] = Field(
        default=["*"],
        description="Allowed HTTP headers"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from environment variables
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Simple initialization without external secret management
    
    @property
    def database_settings(self) -> DatabaseSettings:
        """Get database settings"""
        return DatabaseSettings(
            url=self.database_url,
            echo=self.debug,
            pool_size=10,
            max_overflow=20
        )
    
    # Azure settings removed - simplified configuration
    
    @property
    def social_media_settings(self) -> SocialMediaSettings:
        """Get social media API settings"""
        return SocialMediaSettings(
            facebook_app_id=getattr(self, 'facebook_app_id', None),
            facebook_app_secret=getattr(self, 'facebook_app_secret', None),
            twitter_bearer_token=getattr(self, 'twitter_bearer_token', None),
            twitter_api_key=getattr(self, 'twitter_api_key', None),
            twitter_api_secret=getattr(self, 'twitter_api_secret', None),
            instagram_client_id=getattr(self, 'instagram_client_id', None),
            instagram_client_secret=getattr(self, 'instagram_client_secret', None)
        )
    
    @property
    def threat_detection_settings(self) -> ThreatDetectionSettings:
        """Get threat detection settings"""
        return ThreatDetectionSettings()
    
    @property
    def security_settings(self) -> SecuritySettings:
        """Get security settings"""
        return SecuritySettings(
            secret_key=getattr(self, 'secret_key', 'dev-secret-key-change-in-production'),
            algorithm="HS256",
            access_token_expire_minutes=30
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Configure logging
def setup_logging(settings: Settings):
    """Setup application logging"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Additional logging configuration can be added here if needed