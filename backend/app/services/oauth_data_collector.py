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
from app.models.social_auth_models import (
    SocialAccount, CollectedPost, CollectedConnection, 
    CollectedInteraction, SearchHistory, PostComment, PostLike,
    PlatformType, ConnectionType
)
from app.core.config import get_settings
from app.services.facebook_graph_api_collector import FacebookGraphAPICollector

logger = logging.getLogger(__name__)

class OAuthDataCollector:
    """Collect data using OAuth tokens from connected social accounts"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def collect_data_for_user(self, user_id: str) -> Dict[str, Any]:
        """Collect data from all connected social accounts for a user"""

        collected_data = {
            "posts": [],
            "connections": [],
            "interactions": [],
            "search_histories": []
        }

        warnings = []
        platform_results = {}

        # Get all connected accounts for the user
        accounts = await SocialAccount.find(
            SocialAccount.user_id == user_id,
            SocialAccount.is_active == True
        ).to_list()

        async with aiohttp.ClientSession() as session:
            self.session = session

            for account in accounts:
                try:
                    account_data = await self._collect_from_platform(account)
                    
                    # Track results per platform
                    platform = account.platform.value
                    if platform not in platform_results:
                        platform_results[platform] = {"posts": 0, "connections": 0, "interactions": 0, "search_histories": 0}
                    
                    # Extend collected data
                    collected_data["posts"].extend(account_data.get("posts", []))
                    collected_data["connections"].extend(account_data.get("connections", []))
                    collected_data["interactions"].extend(account_data.get("interactions", []))
                    collected_data["search_histories"].extend(account_data.get("search_histories", []))
                    
                    # Update counts
                    platform_results[platform]["posts"] += len(account_data.get("posts", []))
                    platform_results[platform]["connections"] += len(account_data.get("connections", []))
                    platform_results[platform]["interactions"] += len(account_data.get("interactions", []))
                    platform_results[platform]["search_histories"] += len(account_data.get("search_histories", []))

                    # Update last sync time
                    account.last_sync = datetime.utcnow()
                    await account.save()

                except Exception as e:
                    logger.error(f"Error collecting from {account.platform}: {e}")
                    continue

        # Save collected data to database
        saved_counts = await self._save_collected_data(user_id, collected_data)

        # Add platform-specific warnings
        for platform, counts in platform_results.items():
            if platform == "facebook" and all(count == 0 for count in counts.values()):
                warnings.append({
                    "platform": "facebook",
                    "message": "No Facebook data was collected. This may be due to API permissions or access token expiration.",
                    "recommendation": "Try reconnecting your Facebook account or check app permissions"
                })

        result = {
            "accounts_processed": len(accounts),
            **saved_counts,
            "platform_results": platform_results
        }
        
        if warnings:
            result["warnings"] = warnings

        return result

    async def _save_collected_data(self, user_id: str, collected_data: Dict[str, List]) -> Dict[str, int]:
        """Save all collected data to database"""
        saved_counts = {
            "posts_saved": 0,
            "connections_saved": 0,
            "interactions_saved": 0,
            "search_histories_saved": 0
        }

        # Save posts
        for post_data in collected_data["posts"]:
            try:
                post = CollectedPost(**post_data)
                await post.save()
                saved_counts["posts_saved"] += 1
            except Exception as e:
                logger.error(f"Error saving post: {e}")

        # Save connections
        for conn_data in collected_data["connections"]:
            try:
                connection = CollectedConnection(**conn_data)
                await connection.save()
                saved_counts["connections_saved"] += 1
            except Exception as e:
                logger.error(f"Error saving connection: {e}")

        # Save interactions
        for interaction_data in collected_data["interactions"]:
            try:
                interaction = CollectedInteraction(**interaction_data)
                await interaction.save()
                saved_counts["interactions_saved"] += 1
            except Exception as e:
                logger.error(f"Error saving interaction: {e}")

        # Save search histories
        for search_data in collected_data["search_histories"]:
            try:
                search = SearchHistory(**search_data)
                await search.save()
                saved_counts["search_histories_saved"] += 1
            except Exception as e:
                logger.error(f"Error saving search history: {e}")

        return saved_counts

    async def _collect_from_platform(self, account: SocialAccount) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from a specific platform using OAuth"""

        platform = account.platform.value

        if platform == "facebook":
            return await self._collect_facebook_data(account)
        elif platform == "twitter":
            return await self._collect_twitter_data(account)
        elif platform == "reddit":
            return await self._collect_reddit_data(account)
        elif platform == "youtube":
            return await self._collect_youtube_data(account)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return {"posts": [], "connections": [], "interactions": [], "search_histories": []}

    async def _collect_facebook_data(self, account: SocialAccount) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from Facebook using Graph API"""
        data = {"posts": [], "connections": [], "interactions": [], "search_histories": []}

        try:
            # Use Facebook Graph API collector for reliable data collection
            collector = FacebookGraphAPICollector(
                app_id=get_settings().FACEBOOK_CLIENT_ID,
                app_secret=get_settings().FACEBOOK_CLIENT_SECRET,
                access_token=account.access_token
            )

            # Collect comprehensive user data
            user_data = collector.collect_comprehensive_user_data()

            # Process posts
            for post in user_data.get("posts", []):
                data["posts"].append({
                    "platform": "facebook",
                    "post_id": post.get("id"),
                    "content": post.get("message", ""),
                    "created_at": post.get("created_time"),
                    "url": post.get("permalink_url"),
                    "likes_count": post.get("reactions", {}).get("summary", {}).get("total_count", 0),
                    "comments_count": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                    "shares_count": post.get("shares", {}).get("count", 0) if post.get("shares") else 0,
                    "attachments": post.get("attachments", {}).get("data", []),
                    "account_id": str(account.id)
                })

            # Process friends/connections
            for friend in user_data.get("friends", []):
                data["connections"].append({
                    "platform": "facebook",
                    "connection_type": "friend",
                    "target_user_id": friend.get("id"),
                    "target_username": friend.get("name"),
                    "target_profile_url": f"https://facebook.com/{friend.get('id')}",
                    "relationship": "friend",
                    "account_id": str(account.id)
                })

            # Process photos
            for photo in user_data.get("photos", []):
                data["posts"].append({
                    "platform": "facebook",
                    "post_id": photo.get("id"),
                    "content": photo.get("name", ""),
                    "created_at": photo.get("created_time"),
                    "url": photo.get("source"),
                    "media_type": "photo",
                    "album": photo.get("album", {}).get("name"),
                    "account_id": str(account.id)
                })

            logger.info(f"Successfully collected Facebook data for {account.username}: {len(data['posts'])} posts, {len(data['connections'])} connections")

        except Exception as e:
            logger.error(f"Error in Facebook Graph API data collection: {e}")

        return data

    async def _collect_instagram_data(self, account: SocialAccount) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from Instagram using Graph API"""
        data = {"posts": [], "connections": [], "interactions": [], "search_histories": []}

        try:
            # Collect posts with comments and likes
            if account.collect_posts:
                posts_data = await self._collect_instagram_posts(account)
                data["posts"].extend(posts_data)

            # Collect connections (followers/following)
            if account.collect_connections:
                connections_data = await self._collect_instagram_connections(account)
                data["connections"].extend(connections_data)

            # Collect interactions
            interactions_data = await self._collect_instagram_interactions(account)
            data["interactions"].extend(interactions_data)

        except Exception as e:
            logger.error(f"Error collecting Instagram data: {e}")

        return data

    async def _collect_instagram_posts(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect posts with comments and likes from Instagram"""
        posts = []

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
                                "user_id": account.user_id,
                                "social_account_id": str(account.id),
                                "platform": account.platform,
                                "platform_post_id": media["id"],
                                "content": media.get("caption", ""),
                                "post_url": media.get("permalink", ""),
                                "created_at": datetime.fromisoformat(media["timestamp"].replace('Z', '+00:00')),
                                "likes_count": media.get("like_count", 0),
                                "comments_count": media.get("comments_count", 0),
                                "media_urls": [media.get("media_url")] if media.get("media_url") else [],
                                "likes": [],  # Placeholder
                                "comments": [],  # Placeholder
                                "raw_data": media
                            }
                            posts.append(post_data)

        except Exception as e:
            logger.error(f"Error collecting Instagram data: {e}")

    async def _collect_twitter_data(self, account: SocialAccount) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from Twitter using API v2"""
        data = {"posts": [], "connections": [], "interactions": [], "search_histories": []}

        try:
            # Collect posts with comments and likes
            if account.collect_posts:
                posts_data = await self._collect_twitter_posts(account)
                data["posts"].extend(posts_data)

            # Collect connections (followers/following)
            if account.collect_connections:
                connections_data = await self._collect_twitter_connections(account)
                data["connections"].extend(connections_data)

            # Collect interactions
            interactions_data = await self._collect_twitter_interactions(account)
            data["interactions"].extend(interactions_data)

        except Exception as e:
            logger.error(f"Error collecting Twitter data: {e}")

        return data

    async def _collect_twitter_posts(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect tweets with comments and likes from Twitter"""
        posts = []

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

    async def _collect_reddit_data(self, account: SocialAccount) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from Reddit using API"""
        data = {"posts": [], "connections": [], "interactions": [], "search_histories": []}

        try:
            # Collect posts with comments and likes
            if account.collect_posts:
                posts_data = await self._collect_reddit_posts(account)
                data["posts"].extend(posts_data)

            # Collect connections (subreddits, friends)
            if account.collect_connections:
                connections_data = await self._collect_reddit_connections(account)
                data["connections"].extend(connections_data)

            # Collect interactions
            interactions_data = await self._collect_reddit_interactions(account)
            data["interactions"].extend(interactions_data)

        except Exception as e:
            logger.error(f"Error collecting Reddit data: {e}")

        return data

    async def _collect_reddit_posts(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect posts with comments and likes from Reddit"""
        posts = []

        try:
            # Reddit API endpoint for user's posts - use username instead of 'me'
            username = account.username
            url = f"https://oauth.reddit.com/user/{username}/submitted"
            headers = {
                "Authorization": f"bearer {account.access_token}",
                "User-Agent": "OSINT-Platform/1.0"
            }
            params = {
                "limit": 50,
                "sort": "new"
            }

            print(f"Reddit API URL: {url}")
            print(f"Reddit Username: {username}")
            print(f"Access Token Present: {bool(account.access_token)}")

            async with self.session.get(url, headers=headers, params=params) as response:
                print(f"Reddit API Response Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print(f"Reddit API Response Data Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    print(f"Reddit Posts Found: {len(data.get('data', {}).get('children', []))}")

                    for post in data.get("data", {}).get("children", []):
                        post_data = post["data"]
                        print(f"Processing post: {post_data.get('id')} - {post_data.get('title', '')[:50]}")
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
                else:
                    error_text = await response.text()
                    print(f"Reddit API Error Response: {error_text}")
                    print(f"Reddit API Headers: {dict(response.headers)}")

        except Exception as e:
            logger.error(f"Error collecting Reddit data: {e}")

        return posts

    async def _collect_youtube_data(self, account: SocialAccount) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from YouTube using API"""
        data = {"posts": [], "connections": [], "interactions": [], "search_histories": []}

        try:
            # Collect videos with comments and likes
            if account.collect_posts:
                posts_data = await self._collect_youtube_posts(account)
                data["posts"].extend(posts_data)

            # Collect connections (subscriptions)
            if account.collect_connections:
                connections_data = await self._collect_youtube_connections(account)
                data["connections"].extend(connections_data)

            # Collect interactions
            interactions_data = await self._collect_youtube_interactions(account)
            data["interactions"].extend(interactions_data)

        except Exception as e:
            logger.error(f"Error collecting YouTube data: {e}")

        return data

    async def _collect_youtube_posts(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect videos with comments and likes from YouTube"""
        posts = []

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

    # Placeholder methods for additional data collection
    async def _collect_facebook_connections(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect Facebook friends/connections - Note: user_friends permission is deprecated"""
        # Facebook no longer allows access to user's friends list via API
        # The user_friends permission was deprecated and is no longer available
        logger.info(f"Facebook connections collection not available due to API restrictions for account {account.username}")
        return []

    async def _collect_facebook_interactions(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect Facebook interactions (likes, comments, shares) - Limited due to API restrictions"""
        # Facebook API has restrictions on collecting user interactions
        # Individual likes/comments on others' posts are not accessible via API
        logger.info(f"Facebook interactions collection limited due to API restrictions for account {account.username}")
        return []

    async def _collect_facebook_search_history(self, account: SocialAccount) -> List[Dict[str, Any]]:
        """Collect Facebook search history - Not available via API"""
        # Facebook does not provide search history via their Graph API
        logger.info(f"Facebook search history not available via API for account {account.username}")
        return []

    # Similar placeholder methods would be needed for other platforms
    async def _collect_twitter_connections(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_twitter_interactions(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_twitter_search_history(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_reddit_connections(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_reddit_interactions(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_reddit_search_history(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_youtube_connections(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_youtube_interactions(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []

    async def _collect_youtube_search_history(self, account: SocialAccount) -> List[Dict[str, Any]]:
        return []


# Global instance
oauth_data_collector = OAuthDataCollector()