"""
Selenium Authentication Service for social media platforms
Handles browser automation for authentication and data collection
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SeleniumAuthService:
    """Service for handling Selenium-based authentication"""

    def __init__(self):
        self.active_drivers: Dict[str, webdriver.Chrome] = {}
        self.driver_status: Dict[str, Dict[str, Any]] = {}

    def create_browser_driver(self, user_id: str) -> webdriver.Chrome:
        """Create a new Chrome driver instance for the user"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

            # Add user data directory for persistent sessions
            user_data_dir = f"./data/browser_sessions/{user_id}"
            os.makedirs(user_data_dir, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)

            self.active_drivers[user_id] = driver
            self.driver_status[user_id] = {
                "created_at": datetime.utcnow(),
                "status": "active",
                "platform": None
            }

            return driver

        except Exception as e:
            logger.error(f"Failed to create browser driver for user {user_id}: {e}")
            raise

    async def authenticate_platform(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Authenticate user on a social media platform using Selenium"""
        try:
            driver = self.create_browser_driver(user_id)
            self.driver_status[user_id]["platform"] = platform

            if platform == "facebook":
                return await self._authenticate_facebook(driver, user_id)
            elif platform == "instagram":
                return await self._authenticate_instagram(driver, user_id)
            elif platform == "twitter":
                return await self._authenticate_twitter(driver, user_id)
            elif platform == "reddit":
                return await self._authenticate_reddit(driver, user_id)
            elif platform == "youtube":
                return await self._authenticate_youtube(driver, user_id)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

        except Exception as e:
            logger.error(f"Authentication failed for {platform}: {e}")
            await self.cleanup_driver(user_id)
            raise

    async def _authenticate_facebook(self, driver: webdriver.Chrome, user_id: str) -> Dict[str, Any]:
        """Authenticate Facebook account"""
        try:
            driver.get("https://www.facebook.com")

            # Wait for login form or check if already logged in
            wait = WebDriverWait(driver, 30)

            try:
                # Check if already logged in
                profile_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-pagelet='ProfileActions']"))
                )
                return {
                    "success": True,
                    "message": "Already authenticated with Facebook",
                    "status": "authenticated"
                }
            except TimeoutException:
                # Not logged in, need manual authentication
                return {
                    "success": True,
                    "message": "Facebook login page loaded. Please log in manually.",
                    "status": "needs_manual_login",
                    "url": driver.current_url
                }

        except Exception as e:
            logger.error(f"Facebook authentication error: {e}")
            raise

    async def _authenticate_instagram(self, driver: webdriver.Chrome, user_id: str) -> Dict[str, Any]:
        """Authenticate Instagram account"""
        try:
            driver.get("https://www.instagram.com")

            wait = WebDriverWait(driver, 30)

            try:
                # Check if already logged in
                profile_link = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/accounts/']"))
                )
                return {
                    "success": True,
                    "message": "Already authenticated with Instagram",
                    "status": "authenticated"
                }
            except TimeoutException:
                return {
                    "success": True,
                    "message": "Instagram login page loaded. Please log in manually.",
                    "status": "needs_manual_login",
                    "url": driver.current_url
                }

        except Exception as e:
            logger.error(f"Instagram authentication error: {e}")
            raise

    async def _authenticate_twitter(self, driver: webdriver.Chrome, user_id: str) -> Dict[str, Any]:
        """Authenticate Twitter account"""
        try:
            driver.get("https://twitter.com/login")

            wait = WebDriverWait(driver, 30)

            try:
                # Check if already logged in
                home_timeline = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
                )
                return {
                    "success": True,
                    "message": "Already authenticated with Twitter",
                    "status": "authenticated"
                }
            except TimeoutException:
                return {
                    "success": True,
                    "message": "Twitter login page loaded. Please log in manually.",
                    "status": "needs_manual_login",
                    "url": driver.current_url
                }

        except Exception as e:
            logger.error(f"Twitter authentication error: {e}")
            raise

    async def _authenticate_reddit(self, driver: webdriver.Chrome, user_id: str) -> Dict[str, Any]:
        """Authenticate Reddit account"""
        try:
            driver.get("https://www.reddit.com/login")

            wait = WebDriverWait(driver, 30)

            try:
                # Check if already logged in
                user_menu = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='user-menu']"))
                )
                return {
                    "success": True,
                    "message": "Already authenticated with Reddit",
                    "status": "authenticated"
                }
            except TimeoutException:
                return {
                    "success": True,
                    "message": "Reddit login page loaded. Please log in manually.",
                    "status": "needs_manual_login",
                    "url": driver.current_url
                }

        except Exception as e:
            logger.error(f"Reddit authentication error: {e}")
            raise

    async def _authenticate_youtube(self, driver: webdriver.Chrome, user_id: str) -> Dict[str, Any]:
        """Authenticate YouTube account"""
        try:
            driver.get("https://www.youtube.com")

            wait = WebDriverWait(driver, 30)

            try:
                # Check if already logged in
                avatar_button = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#avatar-btn"))
                )
                return {
                    "success": True,
                    "message": "Already authenticated with YouTube",
                    "status": "authenticated"
                }
            except TimeoutException:
                return {
                    "success": True,
                    "message": "YouTube login page loaded. Please log in manually.",
                    "status": "needs_manual_login",
                    "url": driver.current_url
                }

        except Exception as e:
            logger.error(f"YouTube authentication error: {e}")
            raise

    async def get_browser_status(self, user_id: str) -> Dict[str, Any]:
        """Get the status of the user's browser session"""
        if user_id not in self.driver_status:
            return {
                "status": "inactive",
                "message": "No active browser session"
            }

        status = self.driver_status[user_id]
        driver = self.active_drivers.get(user_id)

        if driver:
            try:
                # Check if driver is still alive
                driver.current_url
                status["status"] = "active"
            except Exception:
                status["status"] = "disconnected"
                # Clean up
                await self.cleanup_driver(user_id)

        return status

    async def load_cookies(self, driver: webdriver.Chrome, platform: str, user_id: str) -> bool:
        """Load saved cookies for the platform"""
        try:
            cookies_file = f"./data/cookies/{user_id}_{platform}_cookies.json"

            if os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)

                for cookie in cookies:
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        logger.warning(f"Failed to add cookie: {e}")

                return True
            else:
                logger.info(f"No saved cookies found for {platform}")
                return False

        except Exception as e:
            logger.error(f"Error loading cookies for {platform}: {e}")
            return False

    async def save_cookies(self, driver: webdriver.Chrome, platform: str, user_id: str):
        """Save cookies for the platform"""
        try:
            cookies = driver.get_cookies()
            cookies_file = f"./data/cookies/{user_id}_{platform}_cookies.json"
            os.makedirs(os.path.dirname(cookies_file), exist_ok=True)

            with open(cookies_file, 'w') as f:
                json.dump(cookies, f)

            logger.info(f"Saved cookies for {platform}")

        except Exception as e:
            logger.error(f"Error saving cookies for {platform}: {e}")

    async def cleanup_driver(self, user_id: str):
        """Clean up the browser driver for the user"""
        try:
            if user_id in self.active_drivers:
                driver = self.active_drivers[user_id]
                driver.quit()
                del self.active_drivers[user_id]

            if user_id in self.driver_status:
                del self.driver_status[user_id]

            logger.info(f"Cleaned up browser session for user {user_id}")

        except Exception as e:
            logger.error(f"Error cleaning up driver for user {user_id}: {e}")


# Global instance
selenium_service = SeleniumAuthService()