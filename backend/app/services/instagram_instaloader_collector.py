"""
Instagram Instaloader Data Collector
Scrapes Instagram data using Instaloader with credentials

This collector:
- Uses Instaloader library to access Instagram data
- Supports both profile and hashtag scraping
- Handles session management for faster subsequent runs
- Saves data to MongoDB with proper error handling
"""

import instaloader
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import time

from app.models.mongo_models import SocialMediaPost, PlatformEnum
from app.core.mongodb import get_mongo_db

logger = logging.getLogger(__name__)

class InstagramInstaloaderCollector:
    """
    Instagram data collector using Instaloader

    Features:
    - Session-based login (faster subsequent runs)
    - Profile and hashtag post collection
    - Media URL extraction
    - Engagement metrics (likes, comments)
    - Hashtag and mention extraction
    """

    def __init__(self, username: str, password: str, session_path: Optional[str] = None, request_delay: float = 1.0, proxy: Optional[str] = None):
        """
        Initialize the Instagram collector

        Args:
            username: Instagram username for login
            password: Instagram password for login
            session_path: Path to save/load session file (optional)
            request_delay: Delay in seconds between requests to avoid rate limiting
            proxy: Proxy URL (e.g., 'http://proxy:port') to use for requests
        """
        self.username = username
        self.password = password
        self.session_path = session_path or "data/browser_sessions/instagram_session"
        self.request_delay = request_delay
        self.proxy = proxy
        self.loader = instaloader.Instaloader()

        # Set proxy if provided
        if self.proxy:
            self.loader.context._session.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
            logger.info(f"Using proxy: {self.proxy}")

        # Create session directory if it doesn't exist
        Path(self.session_path).parent.mkdir(parents=True, exist_ok=True)

    def login(self) -> bool:
        """
        Login to Instagram using credentials

        First tries to load existing session file for faster login.
        If no session exists, performs fresh login with credentials.

        Note: Instagram frequently changes their login process, which may cause
        authentication failures. If login fails, try again later or use different credentials.

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Ensure session directory exists
            session_dir = Path(self.session_path).parent
            session_dir.mkdir(parents=True, exist_ok=True)

            # Try to load existing session (much faster than fresh login)
            self.loader.load_session_from_file(self.username, self.session_path)
            logger.info(f"✅ Loaded existing session for {self.username}")
            return True
        except FileNotFoundError:
            # No existing session, perform fresh login
            logger.info(f"🔐 No existing session found, performing fresh login for {self.username}")
            try:
                self.loader.login(self.username, self.password)
                # Save session for future use
                self.loader.save_session_to_file(self.session_path)
                logger.info(f"✅ Logged in and saved session for {self.username}")
                return True
            except instaloader.exceptions.BadCredentialsException:
                logger.error("❌ Invalid Instagram credentials - please check username and password")
                return False
            except instaloader.exceptions.ConnectionException as e:
                logger.error(f"❌ Connection error during login: {e}")
                logger.error("💡 This might be due to network issues or Instagram rate limiting")
                logger.error("💡 Try using a VPN or different network")
                return False
            except KeyError as e:
                logger.error(f"❌ Instagram login structure changed (CSRF token error): {e}")
                logger.error("💡 Instagram frequently updates their login process")
                logger.error("💡 Try these solutions:")
                logger.error("   1. Wait 1-2 hours and try again")
                logger.error("   2. Use a different Instagram account")
                logger.error("   3. Try logging in manually first, then use the same credentials")
                logger.error("   4. Use a VPN to change your IP address")
                return False
            except instaloader.exceptions.TwoFactorAuthRequiredException:
                logger.error("❌ Two-factor authentication required - not supported by this collector")
                logger.error("💡 Please disable 2FA temporarily or use an account without 2FA")
                logger.error("💡 Alternatively, complete 2FA manually in browser and save session")
                return False
            except Exception as e:
                logger.error(f"❌ Unexpected login error: {type(e).__name__}: {e}")
                logger.error("💡 This could be due to Instagram anti-bot measures")
                logger.error("💡 Try waiting a few hours or using a different account")
                return False
        except Exception as e:
            logger.error(f"❌ Session loading error: {type(e).__name__}: {e}")
            return False

    def collect_posts_from_profile(self, profile_username: str, max_posts: int = 10) -> List[Dict]:
        """
        Collect posts from a specific Instagram profile

        Args:
            profile_username: Instagram username (without @)
            max_posts: Maximum number of posts to collect

        Returns:
            List of post dictionaries with metadata
        """
        posts_data = []

        try:
            # Get profile object from username
            profile = instaloader.Profile.from_username(self.loader.context, profile_username)

            # Iterate through posts (most recent first)
            for post in profile.get_posts():
                if len(posts_data) >= max_posts:
                    break

                # Extract comprehensive post data
                post_data = {
                    "platform": PlatformEnum.INSTAGRAM,
                    "post_id": post.shortcode,  # Unique post identifier
                    "author": profile.username,
                    "author_username": profile.username,
                    "author_name": profile.full_name or profile.username,
                    "content": post.caption or "",  # Post text content
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",  # Direct post URL
                    "posted_at": post.date,  # When post was created
                    "collected_at": datetime.utcnow(),  # When we collected it
                    "engagement_metrics": {
                        "likes": post.likes,
                        "comments": post.comments
                    },
                    "likes_count": post.likes,
                    "comments_count": post.comments,
                    "hashtags": post.caption_hashtags,  # Extracted hashtags
                    "mentions": post.caption_mentions,  # Extracted user mentions
                    # Handle different media types (single image, carousel, video)
                    "media_urls": [node.display_url for node in post.get_sidecar_nodes()] if post.typename == 'GraphSidecar' else [post.url] if post.url else [],
                    "is_processed": False,  # For future processing pipeline
                    "processing_errors": []  # Track any processing issues
                }

                posts_data.append(post_data)

                # Add delay to avoid rate limiting
                time.sleep(self.request_delay)

        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"Profile {profile_username} does not exist")
        except Exception as e:
            logger.error(f"Error collecting posts from {profile_username}: {e}")

        return posts_data

    def collect_hashtag_posts(self, hashtag: str, max_posts: int = 10) -> List[Dict]:
        """
        Collect posts from a specific hashtag

        Args:
            hashtag: Hashtag name (without #)
            max_posts: Maximum number of posts to collect

        Returns:
            List of post dictionaries with metadata
        """
        posts_data = []

        try:
            # Get hashtag posts (most recent first)
            for post in self.loader.get_hashtag_posts(hashtag):
                if len(posts_data) >= max_posts:
                    break

                # Extract post data similar to profile posts
                post_data = {
                    "platform": PlatformEnum.INSTAGRAM,
                    "post_id": post.shortcode,
                    "author": post.owner_username,
                    "author_username": post.owner_username,
                    "content": post.caption or "",
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",
                    "posted_at": post.date,
                    "collected_at": datetime.utcnow(),
                    "engagement_metrics": {
                        "likes": post.likes,
                        "comments": post.comments
                    },
                    "likes_count": post.likes,
                    "comments_count": post.comments,
                    "hashtags": post.caption_hashtags,
                    "mentions": post.caption_mentions,
                    "media_urls": [node.display_url for node in post.get_sidecar_nodes()] if post.typename == 'GraphSidecar' else [post.url] if post.url else [],
                    "is_processed": False,
                    "processing_errors": []
                }

                posts_data.append(post_data)

                # Add delay to avoid rate limiting
                time.sleep(self.request_delay)

        except Exception as e:
            logger.error(f"Error collecting posts from hashtag {hashtag}: {e}")

        return posts_data

    async def save_posts_to_db(self, posts_data: List[Dict]) -> int:
        """
        Save collected posts to MongoDB using raw operations

        Prevents duplicates by checking post_id before insertion.
        Uses async operations for better performance.

        Args:
            posts_data: List of post dictionaries to save

        Returns:
            Number of posts successfully saved
        """
        from app.core.mongodb import get_mongo_db

        saved_count = 0
        db = await get_mongo_db()
        collection = db["social_media_posts"]

        for post_data in posts_data:
            try:
                # Check if post already exists to avoid duplicates
                existing = await collection.find_one({
                    "platform": post_data["platform"],
                    "post_id": post_data["post_id"]
                })

                if existing:
                    logger.info(f"Post {post_data['post_id']} already exists, skipping")
                    continue

                # Insert the new post
                await collection.insert_one(post_data)
                saved_count += 1
                logger.info(f"Saved post {post_data['post_id']}")

            except Exception as e:
                logger.error(f"Error saving post {post_data.get('post_id', 'unknown')}: {e}")

        return saved_count

    async def collect_and_save(self, target: str, target_type: str = "profile", max_posts: int = 10) -> int:
        """
        Collect data and save to database in one operation

        This is the main method that combines login, collection, and saving.
        Handles both profile and hashtag collection types.

        Args:
            target: Username (for profile) or hashtag (for hashtag)
            target_type: "profile" or "hashtag"
            max_posts: Maximum posts to collect

        Returns:
            Number of posts saved to database
        """
        # Ensure we're logged in before collecting
        if not self.login():
            return 0

        # Collect data based on target type
        if target_type == "profile":
            posts_data = self.collect_posts_from_profile(target, max_posts)
        elif target_type == "hashtag":
            posts_data = self.collect_hashtag_posts(target, max_posts)
        else:
            logger.error(f"Unsupported target_type: {target_type}")
            return 0

        # Save collected data to database
        saved_count = await self.save_posts_to_db(posts_data)
        logger.info(f"Collected and saved {saved_count} posts from {target_type} {target}")

        return saved_count

    def collect_feed_posts(self, max_posts: int = 10) -> List[Dict]:
        """
        Collect posts from the user's Instagram feed (timeline)

        Args:
            max_posts: Maximum number of posts to collect

        Returns:
            List of post dictionaries with metadata
        """
        posts_data = []

        try:
            # Get feed posts (what you'd see on the main page)
            for post in self.loader.get_feed_posts():
                if len(posts_data) >= max_posts:
                    break

                # Extract post data similar to profile posts
                post_data = {
                    "platform": PlatformEnum.INSTAGRAM,
                    "post_id": post.shortcode,
                    "author": post.owner_username,
                    "author_username": post.owner_username,
                    "content": post.caption or "",
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",
                    "posted_at": post.date,
                    "collected_at": datetime.utcnow(),
                    "engagement_metrics": {
                        "likes": post.likes,
                        "comments": post.comments
                    },
                    "likes_count": post.likes,
                    "comments_count": post.comments,
                    "hashtags": post.caption_hashtags,
                    "mentions": post.caption_mentions,
                    "media_urls": [node.display_url for node in post.get_sidecar_nodes()] if post.typename == 'GraphSidecar' else [post.url] if post.url else [],
                    "is_processed": False,
                    "processing_errors": [],
                    "source": "feed"  # Indicate this came from feed
                }

                posts_data.append(post_data)

                # Add delay to avoid rate limiting
                time.sleep(self.request_delay)

        except Exception as e:
            logger.error(f"Error collecting feed posts: {e}")

        return posts_data

    def collect_followers(self, profile_username: str, max_followers: int = 100) -> List[Dict]:
        """
        Collect followers from a specific Instagram profile

        Args:
            profile_username: Instagram username (without @)
            max_followers: Maximum number of followers to collect

        Returns:
            List of follower dictionaries with basic profile info
        """
        followers_data = []

        try:
            profile = instaloader.Profile.from_username(self.loader.context, profile_username)

            # Iterate through followers
            for follower in profile.get_followers():
                if len(followers_data) >= max_followers:
                    break

                follower_data = {
                    "platform": PlatformEnum.INSTAGRAM,
                    "relationship_type": "follower",
                    "source_username": profile_username,
                    "target_username": follower.username,
                    "target_full_name": follower.full_name or follower.username,
                    "target_profile_url": f"https://www.instagram.com/{follower.username}/",
                    "is_private": follower.is_private,
                    "is_verified": follower.is_verified,
                    "collected_at": datetime.utcnow(),
                }

                followers_data.append(follower_data)

                # Add delay to avoid rate limiting
                time.sleep(self.request_delay)

        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"Profile {profile_username} does not exist")
        except Exception as e:
            logger.error(f"Error collecting followers from {profile_username}: {e}")

        return followers_data

    def collect_following(self, profile_username: str, max_following: int = 100) -> List[Dict]:
        """
        Collect following (followees) from a specific Instagram profile

        Args:
            profile_username: Instagram username (without @)
            max_following: Maximum number of following to collect

        Returns:
            List of following dictionaries with basic profile info
        """
        following_data = []

        try:
            profile = instaloader.Profile.from_username(self.loader.context, profile_username)

            # Iterate through following
            for followee in profile.get_followees():
                if len(following_data) >= max_following:
                    break

                followee_data = {
                    "platform": PlatformEnum.INSTAGRAM,
                    "relationship_type": "following",
                    "source_username": profile_username,
                    "target_username": followee.username,
                    "target_full_name": followee.full_name or followee.username,
                    "target_profile_url": f"https://www.instagram.com/{followee.username}/",
                    "is_private": followee.is_private,
                    "is_verified": followee.is_verified,
                    "collected_at": datetime.utcnow(),
                }

                following_data.append(followee_data)

                # Add delay to avoid rate limiting
                time.sleep(self.request_delay)

        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"Profile {profile_username} does not exist")
        except Exception as e:
            logger.error(f"Error collecting following from {profile_username}: {e}")

        return following_data

    async def save_relationships_to_db(self, relationships_data: List[Dict]) -> int:
        """
        Save collected relationships to MongoDB

        Args:
            relationships_data: List of relationship dictionaries to save

        Returns:
            Number of relationships successfully saved
        """
        from app.core.mongodb import get_mongo_db

        saved_count = 0
        db = await get_mongo_db()
        collection = db["social_media_relationships"]

        for rel_data in relationships_data:
            try:
                # Check if relationship already exists
                existing = await collection.find_one({
                    "platform": rel_data["platform"],
                    "relationship_type": rel_data["relationship_type"],
                    "source_username": rel_data["source_username"],
                    "target_username": rel_data["target_username"]
                })

                if existing:
                    logger.info(f"Relationship {rel_data['relationship_type']} {rel_data['username']} -> {rel_data['target_username']} already exists, skipping")
                    continue

                # Insert the new relationship
                await collection.insert_one(rel_data)
                saved_count += 1
                logger.info(f"Saved relationship {rel_data['relationship_type']} {rel_data['username']}")

            except Exception as e:
                logger.error(f"Error saving relationship: {e}")

        return saved_count