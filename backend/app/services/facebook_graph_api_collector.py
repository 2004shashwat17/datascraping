"""
Facebook Graph API Data Collector
Official Facebook API - 100% reliable, no browser automation issues
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FacebookGraphAPICollector:
    """Facebook Graph API data collector - official and reliable"""

    def __init__(self, app_id: str, app_secret: str, access_token: Optional[str] = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"
        self.session = requests.Session()

    def get_app_access_token(self) -> str:
        """Get app access token for server-side requests"""
        url = f"{self.base_url}/oauth/access_token"
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "client_credentials"
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()["access_token"]

    def get_user_access_token(self, short_lived_token: str) -> str:
        """Exchange short-lived token for long-lived token"""
        url = f"{self.base_url}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()["access_token"]

    def get_user_profile(self, user_id: str = "me") -> Dict:
        """Get user profile information"""
        url = f"{self.base_url}/{user_id}"
        params = {
            "fields": "id,name,email,first_name,last_name,birthday,gender,location,hometown,about,website,picture",
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_user_posts(self, user_id: str = "me", limit: int = 100) -> List[Dict]:
        """Get user's posts"""
        url = f"{self.base_url}/{user_id}/posts"
        params = {
            "fields": "id,message,story,created_time,updated_time,type,permalink_url,attachments{url,title,description},reactions.summary(true),comments.summary(true)",
            "limit": limit,
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_user_friends(self, user_id: str = "me") -> List[Dict]:
        """Get user's friends (requires friends permission)"""
        url = f"{self.base_url}/{user_id}/friends"
        params = {
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_user_photos(self, user_id: str = "me", limit: int = 100) -> List[Dict]:
        """Get user's photos"""
        url = f"{self.base_url}/{user_id}/photos"
        params = {
            "fields": "id,name,source,created_time,updated_time,album,place,tags",
            "limit": limit,
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_page_info(self, page_id: str) -> Dict:
        """Get Facebook page information"""
        url = f"{self.base_url}/{page_id}"
        params = {
            "fields": "id,name,about,category,description,website,fan_count,rating_count,overall_star_rating",
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_page_posts(self, page_id: str, limit: int = 100) -> List[Dict]:
        """Get page posts"""
        url = f"{self.base_url}/{page_id}/posts"
        params = {
            "fields": "id,message,story,created_time,type,permalink_url,attachments,reactions.summary(true),comments.summary(true)",
            "limit": limit,
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def search_pages(self, query: str, limit: int = 25) -> List[Dict]:
        """Search for Facebook pages"""
        url = f"{self.base_url}/search"
        params = {
            "type": "page",
            "q": query,
            "fields": "id,name,category,about,fan_count",
            "limit": limit,
            "access_token": self.access_token
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def collect_comprehensive_user_data(self, user_id: str = "me") -> Dict:
        """Collect comprehensive user data"""
        try:
            logger.info(f"Collecting comprehensive data for user {user_id}")

            # Get basic profile
            profile = self.get_user_profile(user_id)

            # Get posts
            posts = self.get_user_posts(user_id)

            # Get photos
            photos = self.get_user_photos(user_id)

            # Try to get friends (may fail without permission)
            friends = []
            try:
                friends = self.get_user_friends(user_id)
            except:
                logger.warning("Could not get friends data - missing permissions")

            return {
                "profile": profile,
                "posts": posts,
                "photos": photos,
                "friends": friends,
                "collected_at": datetime.utcnow().isoformat(),
                "data_source": "facebook_graph_api"
            }

        except Exception as e:
            logger.error(f"Error collecting comprehensive user data: {e}")
            raise

# Example usage
if __name__ == "__main__":
    # Example configuration
    collector = FacebookGraphAPICollector(
        app_id="your_app_id",
        app_secret="your_app_secret",
        access_token="user_access_token"
    )

    # Collect user data
    data = collector.collect_comprehensive_user_data()
    print(json.dumps(data, indent=2))