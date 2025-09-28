"""
MongoDB models for social media authentication and data collection
"""
from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class PlatformType(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    TWITTER = "twitter"

class ConnectionType(str, Enum):
    FRIEND = "friend"
    FOLLOWER = "follower"
    FOLLOWING = "following"
    SUBSCRIBER = "subscriber"

class SocialAccount(Document):
    """User's connected social media accounts"""
    user_id: str = Field(..., description="OSINT platform user ID")
    platform: PlatformType
    platform_user_id: str = Field(..., description="User ID on the platform")
    username: str = Field(..., description="Username on the platform")
    display_name: Optional[str] = None
    email: Optional[str] = None
    profile_url: Optional[str] = None
    profile_picture: Optional[str] = None
    
    # OAuth tokens
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    # Account metadata
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync: Optional[datetime] = None
    is_active: bool = True
    
    # Platform-specific data
    platform_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Data collection preferences
    collect_posts: bool = Field(default=True, description="Collect user's posts")
    collect_connections: bool = Field(default=True, description="Collect friends/followers")
    collect_interactions: bool = Field(default=True, description="Collect likes, comments, shares")
    
    class Settings:
        name = "social_accounts"
        indexes = [
            "user_id",
            "platform",
            ("user_id", "platform"),
        ]

class CollectedPost(Document):
    """Posts collected from social media platforms"""
    user_id: str = Field(..., description="OSINT platform user ID")
    social_account_id: str = Field(..., description="Reference to SocialAccount")
    platform: PlatformType
    
    # Post identification
    platform_post_id: str = Field(..., description="Original post ID on platform")
    post_url: Optional[str] = None
    
    # Post content
    content: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    media_type: Optional[str] = None  # photo, video, text, link
    post_type: str = Field(default="post")  # post, comment, story, tweet, video
    
    # Post metadata
    created_at: datetime = Field(..., description="When post was created on platform")
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    language: Optional[str] = None
    location: Optional[str] = None
    
    # Engagement data
    likes_count: Optional[int] = 0
    comments_count: Optional[int] = 0
    shares_count: Optional[int] = 0
    views_count: Optional[int] = 0
    
    # Privacy and visibility
    is_public: bool = Field(default=True)
    visibility: Optional[str] = None  # public, friends, private
    
    # Raw platform data
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "collected_posts"
        indexes = [
            "user_id",
            "platform",
            "social_account_id",
            ("platform", "platform_post_id"),
            "created_at",
        ]

class CollectedConnection(Document):
    """Friends/followers collected from platforms"""
    user_id: str = Field(..., description="OSINT platform user ID")
    social_account_id: str = Field(..., description="Reference to SocialAccount")
    platform: PlatformType
    
    # Connection details
    connection_type: ConnectionType
    platform_user_id: str = Field(..., description="Connected user's platform ID")
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    profile_picture: Optional[str] = None
    
    # Connection metadata
    connected_since: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    
    # Connection stats
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    posts_count: Optional[int] = None
    
    # Raw data
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "collected_connections"
        indexes = [
            "user_id",
            "platform",
            "social_account_id",
            ("platform", "platform_user_id"),
        ]

class CollectedInteraction(Document):
    """User interactions collected from platforms (likes, comments, shares)"""
    user_id: str = Field(..., description="OSINT platform user ID")
    social_account_id: str = Field(..., description="Reference to SocialAccount")
    platform: PlatformType
    
    # Interaction details
    interaction_type: str = Field(..., description="like, comment, share, bookmark, etc.")
    target_type: str = Field(..., description="post, video, tweet, etc.")
    target_id: str = Field(..., description="ID of the target content")
    target_url: Optional[str] = None
    
    # Interaction content (for comments)
    content: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(..., description="When interaction occurred")
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Target content details
    target_author: Optional[str] = None
    target_content: Optional[str] = None
    
    # Raw data
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "collected_interactions"
        indexes = [
            "user_id",
            "platform",
            "social_account_id",
            "interaction_type",
            "created_at",
        ]

class DataCollectionJob(Document):
    """Track data collection jobs for users"""
    user_id: str = Field(..., description="OSINT platform user ID")
    social_account_id: str = Field(..., description="Reference to SocialAccount")
    platform: PlatformType
    
    # Job details
    job_type: str = Field(..., description="posts, connections, interactions, all")
    status: str = Field(default="pending")  # pending, running, completed, failed
    
    # Progress tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_collected: int = Field(default=0)
    items_total: Optional[int] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)
    
    # Job configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "data_collection_jobs"
        indexes = [
            "user_id",
            "status",
            "platform",
            "started_at",
        ]

class OAuthState(Document):
    """Store OAuth state for security verification"""
    state: str = Field(..., description="OAuth state parameter")
    user_id: str = Field(..., description="User ID initiating OAuth")
    platform: PlatformType
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="When state expires")
    is_used: bool = Field(default=False)
    
    class Settings:
        name = "oauth_states"
        indexes = [
            "state",
            "expires_at",
        ]