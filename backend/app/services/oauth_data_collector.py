"""
OAuth-based data collector for social media platforms
Uses stored OAuth tokens to collect user data from connected accounts
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.models.mongo_models import SocialMediaPost, PlatformEnum, ThreatLevelEnum
from app.models.social_auth_models import SocialAccount
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class OAuthDataCollector:
    """Collect data using OAuth tokens from connected social accounts"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def collect_data_for_user(self, user_id: str) -> Dict[str, Any]:
        """Collect data from all connected social accounts for a user"""

        collected_posts = []
        detected_threats = []

        # Get all connected accounts for the user
        accounts = await SocialAccount.find(
            SocialAccount.user_id == user_id,
            SocialAccount.is_active == True
        ).to_list()

        async with aiohttp.ClientSession() as session:
            self.session = session

            for account in accounts:
                try:
                    platform_posts = await self._collect_from_platform(account)
                    collected_posts.extend(platform_posts)

                    # Update last sync time
                    account.last_sync = datetime.utcnow()
                    await account.save()

                except Exception as e:
                    logger.error(f"Error collecting from {account.platform}: {e}")
                    continue

        # Save collected posts to database
        saved_posts = []
        for post_data in collected_posts:
            try:
                post = SocialMediaPost(**post_data)
                await post.save()
                saved_posts.append(post)
            except Exception as e:
                logger.error(f"Error saving post: {e}")
                continue

        return {
            "accounts_processed": len(accounts),
            "posts_collected": len(collected_posts),
            "posts_saved": len(saved_posts),
            "threats_detected": len(detected_threats)
        }

    async def _collect_from_platform(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect data from a specific platform using OAuth"""

        platform = account.platform.value

        if platform == "facebook":
            return await self._collect_facebook_data(account)
        elif platform == "instagram":
            return await self._collect_instagram_data(account)
        elif platform == "twitter":
            return await self._collect_twitter_data(account)
        elif platform == "reddit":
            return await self._collect_reddit_data(account)
        elif platform == "youtube":
            return await self._collect_youtube_data(account)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return []

    async def _collect_facebook_data(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect data from Facebook using Graph API"""
        posts = []

        if not account.collect_posts:
            return posts

        try:
            # Facebook Graph API endpoint for user's posts
            url = f"https://graph.facebook.com/v18.0/me/posts"
            params = {
                "access_token": account.access_token,
                "fields": "id,message,created_time,attachments,likes.summary(true),comments.summary(true),shares",
                "limit": 50
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for post in data.get("data", []):
                        post_data = {
                            "platform": PlatformEnum.FACEBOOK,
                            "post_id": post["id"],
                            "author": account.username,
                            "author_username": account.username,
                            "content": post.get("message", ""),
                            "url": f"https://facebook.com/{post['id']}",
                            "posted_at": datetime.fromisoformat(post["created_time"].replace('Z', '+00:00')),
                            "engagement_metrics": {
                                "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                                "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                                "shares": post.get("shares", {}).get("count", 0) if post.get("shares") else 0
                            },
                            "likes_count": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                            "comments_count": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                            "shares_count": post.get("shares", {}).get("count", 0) if post.get("shares") else 0,
                            "collected_by": account.user_id,
                            "threat_level": ThreatLevelEnum.LOW  # Will be analyzed later
                        }
                        posts.append(post_data)

        except Exception as e:
            logger.error(f"Error collecting Facebook data: {e}")

        return posts

    async def _collect_instagram_data(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect data from Instagram using Graph API"""
        posts = []

        if not account.collect_posts:
            return posts

        try:
            # Instagram Graph API endpoint for user's media
            url = f"https://graph.instagram.com/me/media"
            params = {
                "access_token": account.access_token,
                "fields": "id,media_type,media_url,permalink,caption,timestamp,like_count,comments_count",
                "limit": 50
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for media in data.get("data", []):
                        if media.get("media_type") in ["IMAGE", "CAROUSEL_ALBUM", "VIDEO"]:
                            post_data = {
                                "platform": PlatformEnum.INSTAGRAM,
                                "post_id": media["id"],
                                "author": account.username,
                                "author_username": account.username,
                                "content": media.get("caption", ""),
                                "url": media.get("permalink", ""),
                                "posted_at": datetime.fromisoformat(media["timestamp"].replace('Z', '+00:00')),
                                "engagement_metrics": {
                                    "likes": media.get("like_count", 0),
                                    "comments": media.get("comments_count", 0)
                                },
                                "likes_count": media.get("like_count", 0),
                                "comments_count": media.get("comments_count", 0),
                                "media_urls": [media.get("media_url")] if media.get("media_url") else [],
                                "collected_by": account.user_id,
                                "threat_level": ThreatLevelEnum.LOW
                            }
                            posts.append(post_data)

        except Exception as e:
            logger.error(f"Error collecting Instagram data: {e}")

        return posts

    async def _collect_twitter_data(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect data from Twitter using API v2"""
        posts = []

        if not account.collect_posts:
            return posts

        try:
            # Twitter API v2 endpoint for user's tweets
            url = "https://api.twitter.com/2/users/me/tweets"
            headers = {
                "Authorization": f"Bearer {account.access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "max_results": 50,
                "tweet.fields": "created_at,public_metrics,entities,context_annotations",
                "expansions": "attachments.media_keys",
                "media.fields": "url,type"
            }

            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for tweet in data.get("data", []):
                        metrics = tweet.get("public_metrics", {})
                        post_data = {
                            "platform": PlatformEnum.TWITTER,
                            "post_id": tweet["id"],
                            "author": account.username,
                            "author_username": account.username,
                            "content": tweet.get("text", ""),
                            "url": f"https://twitter.com/i/status/{tweet['id']}",
                            "posted_at": datetime.fromisoformat(tweet["created_at"].replace('Z', '+00:00')),
                            "engagement_metrics": {
                                "likes": metrics.get("like_count", 0),
                                "retweets": metrics.get("retweet_count", 0),
                                "replies": metrics.get("reply_count", 0)
                            },
                            "likes_count": metrics.get("like_count", 0),
                            "shares_count": metrics.get("retweet_count", 0),
                            "comments_count": metrics.get("reply_count", 0),
                            "hashtags": [tag["tag"] for tag in tweet.get("entities", {}).get("hashtags", [])],
                            "collected_by": account.user_id,
                            "threat_level": ThreatLevelEnum.LOW
                        }
                        posts.append(post_data)

        except Exception as e:
            logger.error(f"Error collecting Twitter data: {e}")

        return posts

    async def _collect_reddit_data(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect data from Reddit using API"""
        posts = []

        if not account.collect_posts:
            return posts

        try:
            # Reddit API endpoint for user's posts
            url = "https://oauth.reddit.com/user/me/submitted"
            headers = {
                "Authorization": f"bearer {account.access_token}",
                "User-Agent": "OSINT-Platform/1.0"
            }
            params = {
                "limit": 50,
                "sort": "new"
            }

            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for post in data.get("data", {}).get("children", []):
                        post_data = post["data"]
                        post_obj = {
                            "platform": PlatformEnum.REDDIT,
                            "post_id": post_data["id"],
                            "author": account.username,
                            "author_username": account.username,
                            "content": post_data.get("selftext", "") or post_data.get("title", ""),
                            "url": f"https://reddit.com{post_data['permalink']}",
                            "posted_at": datetime.fromtimestamp(post_data["created_utc"]),
                            "engagement_metrics": {
                                "score": post_data.get("score", 0),
                                "comments": post_data.get("num_comments", 0)
                            },
                            "likes_count": post_data.get("score", 0),
                            "comments_count": post_data.get("num_comments", 0),
                            "collected_by": account.user_id,
                            "threat_level": ThreatLevelEnum.LOW
                        }
                        posts.append(post_obj)

        except Exception as e:
            logger.error(f"Error collecting Reddit data: {e}")

        return posts

    async def _collect_youtube_data(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect data from YouTube using API"""
        posts = []

        if not account.collect_posts:
            return posts

        try:
            # YouTube API endpoint for user's videos
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "forMine": "true",
                "type": "video",
                "maxResults": 50,
                "key": get_settings().YOUTUBE_API_KEY  # Would need to be configured
            }
            headers = {
                "Authorization": f"Bearer {account.access_token}"
            }

            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("items", []):
                        video = item["snippet"]
                        post_data = {
                            "platform": PlatformEnum.YOUTUBE,
                            "post_id": item["id"]["videoId"],
                            "author": account.username,
                            "author_username": account.username,
                            "content": video.get("description", ""),
                            "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                            "posted_at": datetime.fromisoformat(video["publishedAt"].replace('Z', '+00:00')),
                            "media_urls": [video.get("thumbnails", {}).get("default", {}).get("url", "")],
                            "collected_by": account.user_id,
                            "threat_level": ThreatLevelEnum.LOW
                        }
                        posts.append(post_data)

        except Exception as e:
            logger.error(f"Error collecting YouTube data: {e}")

        return posts


# Global instance
oauth_data_collector = OAuthDataCollector()