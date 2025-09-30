"""
Apify Web Scraping Data Collector
Uses Apify actors for scraping various platforms
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

from apify_client import ApifyClient

from app.models.mongo_models import SocialMediaPost, PlatformEnum
from app.core.mongodb import get_database

logger = logging.getLogger(__name__)

class ApifyCollector:
    """Apify data collector for web scraping"""

    def __init__(self, api_token: str):
        self.client = ApifyClient(api_token)
        self.instagram_actor_id = "apidojo/instagram-scraper"  # Popular Instagram scraper actor
        self.twitter_actor_id = "apidojo/tweet-scraper"  # Twitter scraper
        self.youtube_actor_id = "streamers/youtube-scraper"  # YouTube scraper

    async def run_actor(self, actor_id: str, input_data: Dict) -> Optional[Dict]:
        """Run an Apify actor and get results"""
        try:
            # Start the actor
            run = self.client.actor(actor_id).start(input=input_data)

            # Wait for completion
            while True:
                run_info = self.client.run(run["id"]).get()
                if run_info["status"] in ["SUCCEEDED", "FAILED", "ABORTED"]:
                    break
                await asyncio.sleep(5)  # Wait 5 seconds before checking again

            if run_info["status"] != "SUCCEEDED":
                logger.error(f"Actor run failed: {run_info['status']}")
                return None

            # Get dataset items
            dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items
            return {"run_info": run_info, "data": dataset_items}

        except Exception as e:
            logger.error(f"Error running Apify actor {actor_id}: {e}")
            return None

    def parse_instagram_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Parse Instagram scraper results into standard format"""
        posts_data = []

        for item in raw_data:
            try:
                post_data = {
                    "platform": PlatformEnum.INSTAGRAM,
                    "post_id": item.get("id") or item.get("shortCode"),
                    "author": item.get("ownerUsername"),
                    "author_username": item.get("ownerUsername"),
                    "author_name": item.get("ownerFullName") or item.get("ownerUsername"),
                    "content": item.get("caption", ""),
                    "url": item.get("url") or f"https://www.instagram.com/p/{item.get('shortCode')}/",
                    "posted_at": datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00')) if item.get("timestamp") else None,
                    "collected_at": datetime.utcnow(),
                    "engagement_metrics": {
                        "likes": item.get("likesCount", 0),
                        "comments": item.get("commentsCount", 0),
                        "shares": item.get("videoPlayCount", 0) if item.get("type") == "Video" else 0
                    },
                    "likes_count": item.get("likesCount", 0),
                    "comments_count": item.get("commentsCount", 0),
                    "views_count": item.get("videoViewCount") or item.get("videoPlayCount"),
                    "hashtags": item.get("hashtags", []),
                    "mentions": [],  # Apify might not extract mentions directly
                    "media_urls": [item.get("displayUrl")] if item.get("displayUrl") else [],
                    "is_processed": False,
                    "processing_errors": []
                }

                posts_data.append(post_data)

            except Exception as e:
                logger.error(f"Error parsing Instagram item: {e}")

        return posts_data

    def parse_twitter_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Parse Twitter scraper results"""
        posts_data = []

        for item in raw_data:
            try:
                post_data = {
                    "platform": PlatformEnum.TWITTER,
                    "post_id": item.get("id"),
                    "author": item.get("author", {}).get("userName"),
                    "author_username": item.get("author", {}).get("userName"),
                    "author_name": item.get("author", {}).get("fullName") or item.get("author", {}).get("userName"),
                    "content": item.get("text", ""),
                    "url": item.get("url"),
                    "posted_at": datetime.fromisoformat(item["createdAt"].replace('Z', '+00:00')) if item.get("createdAt") else None,
                    "collected_at": datetime.utcnow(),
                    "engagement_metrics": {
                        "likes": item.get("likeCount", 0),
                        "retweets": item.get("retweetCount", 0),
                        "replies": item.get("replyCount", 0)
                    },
                    "likes_count": item.get("likeCount", 0),
                    "shares_count": item.get("retweetCount", 0),
                    "comments_count": item.get("replyCount", 0),
                    "hashtags": item.get("hashtags", []),
                    "mentions": item.get("mentions", []),
                    "media_urls": [media.get("url") for media in item.get("media", []) if media.get("url")],
                    "is_processed": False,
                    "processing_errors": []
                }

                posts_data.append(post_data)

            except Exception as e:
                logger.error(f"Error parsing Twitter item: {e}")

        return posts_data

    async def collect_instagram_profile(self, username: str, max_posts: int = 10) -> List[Dict]:
        """Collect Instagram posts from a profile"""
        input_data = {
            "username": [username],
            "resultsLimit": max_posts
        }

        result = await self.run_actor(self.instagram_actor_id, input_data)
        if not result:
            return []

        return self.parse_instagram_data(result["data"])

    async def collect_twitter_user(self, username: str, max_posts: int = 10) -> List[Dict]:
        """Collect Twitter posts from a user"""
        input_data = {
            "searchTerms": [f"from:{username}"],
            "maxItems": max_posts
        }

        result = await self.run_actor(self.twitter_actor_id, input_data)
        if not result:
            return []

        return self.parse_twitter_data(result["data"])

    async def save_posts_to_db(self, posts_data: List[Dict]) -> int:
        """Save collected posts to MongoDB"""
        saved_count = 0

        for post_data in posts_data:
            try:
                # Check if post already exists
                existing = await SocialMediaPost.find_one(
                    SocialMediaPost.platform == post_data["platform"],
                    SocialMediaPost.post_id == post_data["post_id"]
                )

                if existing:
                    logger.info(f"Post {post_data['post_id']} already exists, skipping")
                    continue

                post = SocialMediaPost(**post_data)
                await post.insert()
                saved_count += 1
                logger.info(f"Saved post {post_data['post_id']}")

            except Exception as e:
                logger.error(f"Error saving post {post_data.get('post_id', 'unknown')}: {e}")

        return saved_count

    async def collect_and_save(self, platform: str, target: str, max_posts: int = 10) -> int:
        """Collect data from specified platform and save to database"""
        if platform == "instagram":
            posts_data = await self.collect_instagram_profile(target, max_posts)
        elif platform == "twitter":
            posts_data = await self.collect_twitter_user(target, max_posts)
        else:
            logger.error(f"Unsupported platform: {platform}")
            return 0

        saved_count = await self.save_posts_to_db(posts_data)
        logger.info(f"Collected and saved {saved_count} posts from {platform} {target}")

        return saved_count