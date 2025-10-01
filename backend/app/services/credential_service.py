"""
Credential-based Data Collection Service
Handles scraping with user credentials for platforms that require login
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from app.services.apify_collector import ApifyCollector
from app.services.twitter_api_io_collector import TwitterApiIOCollector
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class CredentialService:
    """Service for credential-based data collection"""

    def __init__(self):
        self.settings = get_settings()

    async def collect_instagram_data(self, email: str, password: str, target_username: str, max_posts: int = 10) -> Dict[str, int]:
        """Collect Instagram data using Apify (API-based)"""
        try:
            logger.info(f"Starting Instagram collection for {target_username} using Apify")
            
            # Use Apify for Instagram collection (API-based, no browser automation)
            api_token = self.settings.apify_api_token
            if not api_token:
                return {
                    "success": False,
                    "error": "Apify API token not configured",
                    "collected_posts": 0,
                    "platform": "instagram",
                    "target": target_username
                }

            collector = ApifyCollector(api_token)
            collected_count = await collector.collect_and_save(
                platform="instagram",
                target=target_username,
                max_posts=max_posts
            )
            logger.info(f"Instagram collection completed, saved {collected_count} posts")

            return {
                "success": True,
                "collected_posts": collected_count,
                "platform": "instagram",
                "target": target_username
            }

        except Exception as e:
            logger.error(f"Error in Instagram collection: {e}")
            return {
                "success": False,
                "error": str(e),
                "collected_posts": 0,
                "platform": "instagram",
                "target": target_username
            }

    async def collect_comprehensive_instagram_data(self, email: str, password: str, max_items: int = 50) -> Dict[str, int]:
        """Collect comprehensive Instagram data - NOT AVAILABLE in API-only mode"""
        logger.warning("Comprehensive Instagram collection not available in API-only mode")
        return {
            "success": False,
            "error": "Comprehensive Instagram collection requires browser automation, not available in API-only mode",
            "collected_posts": 0,
            "collected_followers": 0,
            "collected_following": 0,
            "platform": "instagram",
            "target": email
        }

    async def collect_twitter_data(self, username: str, max_posts: int = 10) -> Dict[str, int]:
        """Collect Twitter data using TwitterApiIOCollector"""
        try:
            logger.info(f"Starting Twitter collection for {username} using TwitterApiIO")

            # Get Twitter API IO key from settings
            api_key = getattr(self.settings, 'twitter_api_io_key', None)
            if not api_key:
                return {
                    "success": False,
                    "error": "TwitterApiIO API key not configured",
                    "collected_posts": 0,
                    "platform": "twitter",
                    "target": username
                }

            async with TwitterApiIOCollector(api_key) as collector:
                collected_count = await collector.collect_and_save(
                    platform="twitter",
                    target=username,
                    max_posts=max_posts
                )

            logger.info(f"Twitter collection completed, saved {collected_count} posts")

            return {
                "success": True,
                "collected_posts": collected_count,
                "platform": "twitter",
                "target": username
            }

        except Exception as e:
            logger.error(f"Error in Twitter collection: {e}")
            return {
                "success": False,
                "error": str(e),
                "collected_posts": 0,
                "platform": "twitter",
                "target": username
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

        elif platform == "twitter":
            # Use TwitterApiIO for Twitter
            return await self.collect_twitter_data(
                username=target,
                max_posts=max_posts
            )

        elif platform == "youtube":
            # Use Apify for YouTube
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