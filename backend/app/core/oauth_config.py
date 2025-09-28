"""
OAuth configuration for social media platforms
"""
from pydantic_settings import BaseSettings
from typing import Dict, List

class OAuthSettings(BaseSettings):
    # Facebook/Instagram (Meta)
    FACEBOOK_CLIENT_ID: str = ""
    FACEBOOK_CLIENT_SECRET: str = ""
    FACEBOOK_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/facebook/callback"
    
    # Instagram (uses Facebook API)
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/instagram/callback"
    
    # Reddit
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/reddit/callback"
    
    # YouTube (Google)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8001/api/v1/oauth/google/callback"
    
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
        "scopes": ["public_profile", "email", "user_posts", "user_friends", "pages_read_engagement"]
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
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "api_base": "https://www.googleapis.com/youtube/v3",
        "scopes": [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
    },
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "api_base": "https://api.twitter.com/2",
        "scopes": ["tweet.read", "users.read", "follows.read", "like.read", "bookmark.read"]
    }
}

# Data types that can be collected from each platform
PLATFORM_DATA_TYPES = {
    "facebook": {
        "posts": "User's posts and status updates",
        "friends": "Friends list (limited by API)",
        "likes": "Liked pages and posts",
        "photos": "Photos and albums",
        "events": "Events user is attending"
    },
    "instagram": {
        "posts": "User's photos and videos",
        "stories": "Story highlights",
        "media": "All media content"
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
    },
    "twitter": {
        "tweets": "User's tweets and retweets",
        "followers": "Followers list",
        "following": "Following list",
        "likes": "Liked tweets",
        "bookmarks": "Bookmarked tweets"
    }
}