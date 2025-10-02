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

class PostComment(BaseModel):
    """Individual comment on a post"""
    comment_id: str = Field(..., description="Unique comment ID on platform")
    author_id: str = Field(..., description="Comment author's platform ID")
    author_username: Optional[str] = None
    author_display_name: Optional[str] = None
    content: str
    created_at: datetime
    likes_count: int = 0
    replies_count: int = 0
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class PostLike(BaseModel):
    """Individual like on a post"""
    user_id: str = Field(..., description="Liking user's platform ID")
    username: Optional[str] = None
    display_name: Optional[str] = None
    liked_at: datetime
    raw_data: Dict[str, Any] = Field(default_factory=dict)

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
    
    # Individual engagement details
    likes: List[PostLike] = Field(default_factory=list)
    comments: List[PostComment] = Field(default_factory=list)
    
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
    
    # PKCE support for Twitter
    code_verifier: Optional[str] = None
    
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

class SearchHistory(Document):
    """User's search history and interactions on social platforms"""
    user_id: str = Field(..., description="OSINT platform user ID")
    social_account_id: str = Field(..., description="Reference to SocialAccount")
    platform: PlatformType
    
    # Search details
    search_query: str = Field(..., description="The search query performed")
    search_type: str = Field(default="general")  # general, hashtag, user, location, etc.
    
    # Interaction details (for tracking interactions on search results)
    interaction_type: Optional[str] = None  # like, comment, share, view, etc.
    target_content_id: Optional[str] = None  # ID of the content interacted with
    target_content_type: Optional[str] = None  # post, comment, profile, etc.
    
    # Metadata
    searched_at: datetime = Field(default_factory=datetime.utcnow)
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional data
    results_count: Optional[int] = None  # Number of results returned
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "search_histories"
        indexes = [
            "user_id",
            "platform",
            "social_account_id",
            "searched_at",
            ("search_query", "platform"),
        ]