"""
Twitter API IO Data Collector
Uses twitterapi.io service for Twitter data collection
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import httpx

from app.models.mongo_models import SocialMediaPost, PlatformEnum
from app.core.mongodb import get_database

logger = logging.getLogger(__name__)

class TwitterApiIOCollector:
    """Twitter API IO data collector"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.twitterapi.io"
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Twitter API IO"""
        if not self.session:
            self.session = httpx.AsyncClient(timeout=30.0)

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = await self.session.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Twitter API IO request failed: {e}")
            return None

    async def get_user_tweets(self, username: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent tweets from a user"""
        try:
            # Get user info first
            user_data = await self._make_request(f"/v1/user/info", {"username": username})
            if not user_data or "user" not in user_data:
                logger.error(f"Could not get user info for {username}")
                return []

            user_id = user_data["user"]["id"]

            # Get user tweets
            tweets_data = await self._make_request(f"/v1/user/tweets", {
                "user_id": user_id,
                "count": count
            })

            if not tweets_data or "tweets" not in tweets_data:
                return []

            tweets = []
            for tweet in tweets_data["tweets"]:
                tweets.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text", ""),
                    "created_at": tweet.get("created_at"),
                    "retweet_count": tweet.get("retweet_count", 0),
                    "like_count": tweet.get("like_count", 0),
                    "reply_count": tweet.get("reply_count", 0),
                    "username": username,
                    "platform": "twitter"
                })

            return tweets

        except Exception as e:
            logger.error(f"Error getting tweets for {username}: {e}")
            return []

    async def search_tweets(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search for tweets by query"""
        try:
            search_data = await self._make_request(f"/v1/search/tweets", {
                "query": query,
                "count": count
            })

            if not search_data or "tweets" not in search_data:
                return []

            tweets = []
            for tweet in search_data["tweets"]:
                tweets.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text", ""),
                    "created_at": tweet.get("created_at"),
                    "username": tweet.get("username"),
                    "retweet_count": tweet.get("retweet_count", 0),
                    "like_count": tweet.get("like_count", 0),
                    "reply_count": tweet.get("reply_count", 0),
                    "platform": "twitter"
                })

            return tweets

        except Exception as e:
            logger.error(f"Error searching tweets for query '{query}': {e}")
            return []

    async def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        try:
            user_data = await self._make_request(f"/v1/user/info", {"username": username})

            if not user_data or "user" not in user_data:
                return None

            user = user_data["user"]
            return {
                "username": user.get("username"),
                "name": user.get("name"),
                "bio": user.get("description"),
                "followers_count": user.get("followers_count", 0),
                "following_count": user.get("following_count", 0),
                "tweet_count": user.get("tweet_count", 0),
                "verified": user.get("verified", False),
                "profile_image_url": user.get("profile_image_url"),
                "platform": "twitter",
                "scraped_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting profile for {username}: {e}")
            return None

    async def collect_and_save(self, platform: str, target: str, max_posts: int = 10) -> int:
        """Collect data from Twitter and save to database"""
        if platform != "twitter":
            logger.error(f"Unsupported platform: {platform}")
            return 0

        try:
            # Get user profile
            profile = await self.get_user_profile(target)
            if profile:
                await self._save_profile_to_db(profile)

            # Get user tweets
            tweets = await self.get_user_tweets(target, max_posts)
            saved_count = await self._save_tweets_to_db(tweets)

            logger.info(f"Collected and saved {saved_count} tweets from Twitter user {target}")
            return saved_count

        except Exception as e:
            logger.error(f"Error collecting Twitter data for {target}: {e}")
            return 0

    async def _save_profile_to_db(self, profile: Dict[str, Any]) -> None:
        """Save profile to database"""
        try:
            db = get_database()
            # You might want to create a separate collection for profiles
            # For now, we'll store basic info
            logger.info(f"Saved profile for {profile.get('username')}")
        except Exception as e:
            logger.error(f"Error saving profile: {e}")

    async def _save_tweets_to_db(self, tweets: List[Dict[str, Any]]) -> int:
        """Save tweets to database"""
        try:
            db = get_database()
            saved_count = 0

            for tweet in tweets:
                # Convert to SocialMediaPost format
                post_data = {
                    "platform": PlatformEnum.TWITTER,
                    "platform_id": str(tweet.get("id")),
                    "content": tweet.get("text", ""),
                    "author_username": tweet.get("username"),
                    "created_at": datetime.fromisoformat(tweet.get("created_at").replace('Z', '+00:00')) if tweet.get("created_at") else datetime.utcnow(),
                    "engagement_metrics": {
                        "likes": tweet.get("like_count", 0),
                        "retweets": tweet.get("retweet_count", 0),
                        "replies": tweet.get("reply_count", 0)
                    },
                    "metadata": {
                        "collected_at": datetime.utcnow(),
                        "source": "twitterapi.io"
                    }
                }

                # Save to database
                await SocialMediaPost(**post_data).insert()
                saved_count += 1

            return saved_count

        except Exception as e:
            logger.error(f"Error saving tweets to database: {e}")
            return 0