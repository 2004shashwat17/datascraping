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
    
    # Instagram (Meta)
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/instagram/callback"
    
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
    "instagram": {
        "auth_url": "https://api.instagram.com/oauth/authorize",
        "token_url": "https://api.instagram.com/oauth/access_token",
        "api_base": "https://graph.instagram.com",
        "scopes": ["user_profile", "user_media"]
    },
    "reddit": {
        "auth_url": "https://www.reddit.com/api/v1/authorize",
        "token_url": "https://www.reddit.com/api/v1/access_token",
        "api_base": "https://oauth.reddit.com",
        "scopes": ["identity", "read", "history", "subscribe", "privatemessages"]
    },
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "api_base": "https://api.twitter.com/2",
        "scopes": ["tweet.read", "users.read", "follows.read", "like.read"]
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
    "instagram": {
        "posts": "User's Instagram posts and media",
        "profile": "Profile information and bio",
        "followers": "Follower count and basic info",
        "following": "Following list"
    },
    "reddit": {
        "posts": "Submitted posts and comments",
        "subscriptions": "Subscribed subreddits", 
        "saved": "Saved posts and comments",
        "history": "Comment and post history"
    },
    "twitter": {
        "tweets": "User's tweets and replies",
        "profile": "Profile information",
        "followers": "Follower information",
        "following": "Following list",
        "likes": "Liked tweets"
    }
}