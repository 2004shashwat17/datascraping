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
        if platform == "instagram":
            if "email" not in credentials or "password" not in credentials:
                return {
                    "success": False,
                    "error": "Email and password required for Instagram",
                    "collected_posts": 0,
                    "platform": platform,
                    "target": target
                }

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