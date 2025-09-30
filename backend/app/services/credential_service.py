"""
Credential-based Data Collection Service
Handles scraping with user credentials for platforms that require login
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from app.services.instagram_instaloader_collector import InstagramInstaloaderCollector
from app.services.apify_collector import ApifyCollector
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class CredentialService:
    """Service for credential-based data collection"""

    def __init__(self):
        self.settings = get_settings()

    async def collect_instagram_data(self, email: str, password: str, target_username: str, max_posts: int = 10) -> Dict[str, int]:
        """Collect Instagram data using Instaloader with credentials"""
        try:
            logger.info(f"Starting Instagram collection for {email} -> {target_username}")
            collector = InstagramInstaloaderCollector(
                username=email,  # Instagram uses email/username
                password=password,
                session_path=f"data/browser_sessions/instagram_{email.replace('@', '_').replace('.', '_')}"
            )
            logger.info("InstagramInstaloaderCollector created")

            collected_count = await collector.collect_and_save(
                target=target_username,
                target_type="profile",
                max_posts=max_posts
            )
            logger.info(f"Collection completed, saved {collected_count} posts")

            return {
                "success": True,
                "collected_posts": collected_count,
                "platform": "instagram",
                "target": target_username
            }

        except Exception as e:
            logger.error(f"Error collecting Instagram data: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "collected_posts": 0,
                "platform": "instagram",
                "target": target_username
            }

    async def collect_comprehensive_instagram_data(self, email: str, password: str, max_items: int = 50) -> Dict[str, int]:
        """Collect comprehensive Instagram data for the logged-in user"""
        logger.info(f"Starting comprehensive Instagram collection for {email} with max_items={max_items}")
        try:
            logger.info(f"Starting comprehensive Instagram collection for {email}")
            collector = InstagramInstaloaderCollector(
                username=email,
                password=password,
                session_path=f"data/browser_sessions/instagram_{email.replace('@', '_').replace('.', '_')}",
                request_delay=2.0  # Slower to avoid detection
            )

            total_collected = 0

            # 1. Collect feed posts
            logger.info("Collecting feed posts...")
            feed_posts = collector.collect_feed_posts(max_posts=max_items)
            feed_saved = await collector.save_posts_to_db(feed_posts)
            total_collected += feed_saved
            logger.info(f"Saved {feed_saved} feed posts")

            # 2. Collect user's own posts
            logger.info("Collecting own profile posts...")
            own_posts = collector.collect_posts_from_profile(email, max_posts=max_items)
            own_saved = await collector.save_posts_to_db(own_posts)
            total_collected += own_saved
            logger.info(f"Saved {own_saved} own posts")

            # 3. Collect followers
            logger.info("Collecting followers...")
            followers = collector.collect_followers(email, max_followers=max_items)
            followers_saved = await collector.save_relationships_to_db(followers)
            logger.info(f"Saved {followers_saved} followers")

            # 4. Collect following
            logger.info("Collecting following...")
            following = collector.collect_following(email, max_following=max_items)
            following_saved = await collector.save_relationships_to_db(following)
            logger.info(f"Saved {following_saved} following")

            logger.info(f"Comprehensive collection completed: {total_collected} posts, {followers_saved} followers, {following_saved} following")

            return {
                "success": True,
                "collected_posts": total_collected,
                "collected_followers": followers_saved,
                "collected_following": following_saved,
                "platform": "instagram",
                "target": email
            }

        except Exception as e:
            logger.error(f"Error in comprehensive Instagram collection: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "collected_posts": 0,
                "collected_followers": 0,
                "collected_following": 0,
                "platform": "instagram",
                "target": email
            }

    async def collect_with_apify(self, platform: str, target: str, api_token: Optional[str] = None, max_posts: int = 10) -> Dict[str, int]:
        """Collect data using Apify for platforms that support it"""
        try:
            api_token = api_token or self.settings.apify_api_token
            if not api_token:
                return {
                    "success": False,
                    "error": "Apify API token not configured",
                    "collected_posts": 0,
                    "platform": platform,
                    "target": target
                }

            collector = ApifyCollector(api_token)

            collected_count = await collector.collect_and_save(
                platform=platform,
                target=target,
                max_posts=max_posts
            )

            return {
                "success": True,
                "collected_posts": collected_count,
                "platform": platform,
                "target": target
            }

        except Exception as e:
            logger.error(f"Error collecting {platform} data with Apify: {e}")
            return {
                "success": False,
                "error": str(e),
                "collected_posts": 0,
                "platform": platform,
                "target": target
            }

    async def collect_data(self, platform: str, credentials: Dict[str, str], target: str, max_posts: int = 10) -> Dict[str, int]:
        """Main method to collect data based on platform and credentials"""
        logger.info(f"collect_data called: platform={platform}, target='{target}', max_posts={max_posts}")
        
        if platform == "instagram":
            if "email" not in credentials or "password" not in credentials:
                return {
                    "success": False,
                    "error": "Email and password required for Instagram",
                    "collected_posts": 0,
                    "platform": platform,
                    "target": target
                }

            # If target is empty, "self", or same as email, do comprehensive collection
            if not target or target.lower() in ["self", "me", credentials["email"].lower()]:
                logger.info(f"Using comprehensive collection for Instagram (target='{target}')")
                return await self.collect_comprehensive_instagram_data(
                    email=credentials["email"],
                    password=credentials["password"],
                    max_items=max_posts
                )
            else:
                # Collect from specific target
                logger.info(f"Using regular collection for Instagram target='{target}'")
                return await self.collect_instagram_data(
                    email=credentials["email"],
                    password=credentials["password"],
                    target_username=target,
                    max_posts=max_posts
                )

        elif platform in ["twitter", "youtube"]:
            # Use Apify for these platforms
            api_token = credentials.get("api_token")
            return await self.collect_with_apify(
                platform=platform,
                target=target,
                api_token=api_token,
                max_posts=max_posts
            )

        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}",
                "collected_posts": 0,
                "platform": platform,
                "target": target
            }