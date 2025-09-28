"""
MongoDB document models using Beanie ODM for the OSINT platform.
These replace the SQLAlchemy models for document-based storage.
"""

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field, BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PlatformEnum(str, Enum):
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    REDDIT = "reddit"


class ThreatLevelEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# User Document
class User(Document):
    """User document model"""
    username: str = Field(..., description="Unique username")
    email: str = Field(..., description="Unique email address")
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Social Media Platform Permissions
    enabled_platforms: List[PlatformEnum] = Field(default_factory=list)
    permissions_granted: bool = False
    last_permissions_update: Optional[datetime] = None
    
    class Settings:
        name = "users"


# Social Media Post Document
class SocialMediaPost(Document):
    """Social media post document model"""
    platform: PlatformEnum
    post_id: str = Field(..., description="Unique post identifier")
    author: Optional[str] = None  # Author username/handle
    author_username: Optional[str] = None
    author_name: Optional[str] = None
    content: str
    url: Optional[str] = None  # URL to the post
    posted_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Engagement metrics
    engagement_metrics: Dict[str, Any] = Field(default_factory=dict)
    likes_count: int = 0
    shares_count: int = 0
    comments_count: int = 0
    views_count: Optional[int] = None
    
    # Analysis results
    threat_level: ThreatLevelEnum = ThreatLevelEnum.LOW
    threat_score: float = Field(0.0, ge=0.0, le=1.0)
    sentiment: Optional[SentimentEnum] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    
    # Metadata
    language: Optional[str] = None
    location: Optional[str] = None
    hashtags: List[str] = []
    mentions: List[str] = []
    urls: List[str] = []
    media_urls: List[str] = []
    
    # Collection metadata
    collected_by: Optional[PydanticObjectId] = None
    
    # Processing status
    is_processed: bool = False
    processing_errors: List[str] = []
    
    class Settings:
        name = "social_media_posts"
        indexes = [
            [("platform", 1), ("post_id", 1)],  # Compound index for uniqueness
            [("posted_at", -1)],  # Index for time-based queries
            [("threat_level", 1)],
            [("collected_at", -1)],
        ]


# Threat Detection Document
class ThreatDetection(Document):
    """Threat detection result document"""
    platform: PlatformEnum
    post_id: str  # Reference to SocialMediaPost._id as string
    threat_type: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    severity: str  # "critical", "high", "medium", "low"
    description: Optional[str] = None
    
    # Detection metadata
    detection_method: str = "keyword_matching"  # e.g., "keyword_matching", "ml_classifier", "sentiment_analysis"
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    detected_by: Optional[PydanticObjectId] = None
    is_validated: bool = False
    is_false_positive: bool = False
    is_confirmed: bool = False
    
    # Additional context
    keywords_matched: List[str] = []
    ml_model_version: Optional[str] = None
    confidence_threshold: Optional[float] = None
    source_url: Optional[str] = None
    
    class Settings:
        name = "threat_detections"
        indexes = [
            [("post_id", 1)],
            [("threat_type", 1)],
            [("detected_at", -1)],
            [("severity", 1)],
        ]


# Trend Analysis Document
class TrendAnalysis(Document):
    """Trend analysis document"""
    trend_name: str
    trend_type: str  # e.g., "hashtag", "keyword", "topic"
    
    # Time period
    start_time: datetime
    end_time: datetime
    
    # Metrics
    mentions_count: int = 0
    engagement_total: int = 0
    velocity: float = 0.0  # mentions per hour
    growth_rate: float = 0.0  # percentage change
    
    # Geographic and platform distribution
    platform_distribution: Dict[str, int] = {}
    geographic_distribution: Dict[str, int] = {}
    
    # Threat assessment
    threat_relevance: ThreatLevelEnum = ThreatLevelEnum.LOW
    threat_indicators: List[str] = []
    
    # Analysis metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_method: str = "statistical"
    confidence_level: float = Field(0.0, ge=0.0, le=1.0)
    
    class Settings:
        name = "trend_analyses"
        indexes = [
            [("trend_name", 1)],
            [("start_time", -1)],
            [("analyzed_at", -1)],
            [("threat_relevance", 1)],
        ]


# Collection Job Document  
class CollectionJob(Document):
    """Data collection job tracking document"""
    job_name: str
    platforms: List[PlatformEnum]
    keywords: List[str] = []
    location_filters: List[str] = []
    
    # Job status
    status: str = "pending"  # pending, running, completed, failed
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0)
    
    # Results
    posts_collected: int = 0
    errors_encountered: int = 0
    
    # Timing
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    created_by: Optional[str] = None  # Reference to User._id as string
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "collection_jobs"
        indexes = [
            [("status", 1)],
            [("created_at", -1)],
            [("scheduled_for", 1)],
        ]


# Analytics Summary Document
class AnalyticsSummary(Document):
    """Daily/hourly analytics summary document"""
    summary_type: str  # "hourly", "daily", "weekly"
    summary_date: datetime
    
    # Post metrics
    total_posts: int = 0
    posts_by_platform: Dict[str, int] = {}
    posts_by_threat_level: Dict[str, int] = {}
    
    # Threat metrics
    total_threats: int = 0
    threats_by_type: Dict[str, int] = {}
    threats_by_severity: Dict[str, int] = {}
    
    # Engagement metrics
    total_engagement: int = 0
    average_engagement: float = 0.0
    
    # Top entities
    top_hashtags: List[Dict[str, Any]] = []
    top_mentions: List[Dict[str, Any]] = []
    top_authors: List[Dict[str, Any]] = []
    
    # Geographic distribution
    geographic_activity: Dict[str, int] = {}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "analytics_summaries"
        indexes = [
            [("summary_type", 1), ("summary_date", -1)],
            [("created_at", -1)],
        ]