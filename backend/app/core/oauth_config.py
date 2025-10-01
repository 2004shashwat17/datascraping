"""
OAuth configuration for social media platforms
"""
from pydantic_settings import BaseSettings
from typing import Dict, List

class OAuthSettings(BaseSettings):
    # Facebook/Instagram (Meta) - Instagram access through Facebook Graph API
    FACEBOOK_CLIENT_ID: str = ""
    FACEBOOK_CLIENT_SECRET: str = ""
    FACEBOOK_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/facebook/callback"
    
    # Reddit
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/reddit/callback"
    
    # Twitter
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    TWITTER_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/twitter/callback"

    class Config:
        env_file = ".env"
        extra = "ignore"

oauth_settings = OAuthSettings()

# Platform configurations with OAuth URLs and scopes
PLATFORM_CONFIGS = {
    "facebook": {
        "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "api_base": "https://graph.facebook.com/v18.0",
        "scopes": ["public_profile", "email", "pages_read_engagement", "pages_show_list", "instagram_basic", "instagram_content_publish", "pages_read_engagement"]
    },
    "reddit": {
        "auth_url": "https://www.reddit.com/api/v1/authorize",
        "token_url": "https://www.reddit.com/api/v1/access_token",
        "api_base": "https://oauth.reddit.com",
        "scopes": ["identity", "read", "history", "subscribe", "privatemessages"]
    }
}

# Data types that can be collected from each platform
PLATFORM_DATA_TYPES = {
    "facebook": {
        "posts": "User's posts and status updates",
        "friends": "Friends list (limited by API)",
        "likes": "Liked pages and posts",
        "photos": "Photos and albums",
        "events": "Events user is attending",
        "instagram_posts": "Instagram posts and stories",
        "instagram_media": "Instagram photos and videos",
        "instagram_insights": "Instagram account insights"
    },
    "reddit": {
        "posts": "Submitted posts and comments",
        "subscriptions": "Subscribed subreddits", 
        "saved": "Saved posts and comments",
        "history": "Comment and post history"
    },
    "google": {
        "videos": "YouTube videos and playlists",
        "subscriptions": "Channel subscriptions",
        "likes": "Liked videos",
        "comments": "Video comments"
    }
}