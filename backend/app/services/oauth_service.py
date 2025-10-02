"""
OAuth service for social media platform authentication
"""
import httpx
import secrets
import base64
import asyncio
import os
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs

from app.core.config import get_settings
from app.core.oauth_config import oauth_settings
from app.core.mongodb import get_database
from app.models.social_auth_models import SocialAccount, OAuthState, PlatformType
from app.core.oauth_config import PLATFORM_CONFIGS
from app.services import oauth_data_collector
import logging

logger = logging.getLogger(__name__)

class OAuthService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_authorization_url(self, platform: str, user_id: str) -> Tuple[str, str]:
        """Generate OAuth authorization URL for a platform"""
        if platform not in PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")
        
        # Determine actual platform for API calls (no longer needed for Instagram)
        actual_platform = platform
        
        # Check if we're in test mode
        if os.getenv("TESTING", "false").lower() == "true":
            # Return mock URL for testing
            state = secrets.token_urlsafe(32)
            await self._store_oauth_state(state, user_id, platform)
            mock_url = f"http://localhost:3000/oauth-mock/{platform}?state={state}"
            return mock_url, state
        
        config = PLATFORM_CONFIGS[actual_platform]
        state = secrets.token_urlsafe(32)
        
        # Generate code_verifier for Twitter PKCE
        code_verifier = None
        if platform == "twitter":
            code_verifier = secrets.token_urlsafe(32)
        
        # Store state for security verification
        await self._store_oauth_state(state, user_id, platform, code_verifier)
        
        client_id_map = {
            "facebook": oauth_settings.FACEBOOK_CLIENT_ID,
            "instagram": oauth_settings.INSTAGRAM_CLIENT_ID,
            "reddit": oauth_settings.REDDIT_CLIENT_ID,
            "twitter": oauth_settings.TWITTER_CLIENT_ID,
        }
        
        redirect_uri_map = {
            "facebook": oauth_settings.FACEBOOK_REDIRECT_URI,
            "instagram": oauth_settings.INSTAGRAM_REDIRECT_URI,
            "reddit": oauth_settings.REDDIT_REDIRECT_URI,
            "twitter": oauth_settings.TWITTER_REDIRECT_URI,
        }
        
        client_id = client_id_map.get(actual_platform)
        redirect_uri = redirect_uri_map.get(actual_platform)
        
        if not client_id or client_id == f"your_{actual_platform}_client_id_here":
            raise ValueError(f"Client ID not configured for {platform}. Please set {actual_platform.upper()}_CLIENT_ID in your .env file")
        
        if not redirect_uri:
            raise ValueError(f"Redirect URI not configured for {platform}")
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(config["scopes"]),
            "state": state,
            "response_type": "code"
        }
        
        # Platform-specific parameters
        if platform == "reddit":
            params["duration"] = "permanent"
        elif platform == "twitter":
            params["code_challenge_method"] = "S256"
            params["code_challenge"] = self._generate_code_challenge(code_verifier)
        
        auth_url = f"{config['auth_url']}?{urlencode(params)}"
        
        return auth_url, state
    
    async def handle_callback(self, platform: str, code: str, state: str) -> Dict:
        """Handle OAuth callback and exchange code for tokens"""
        # Verify state
        stored_data = await self._verify_oauth_state(state, platform)
        if not stored_data:
            raise ValueError("Invalid or expired OAuth state")
        
        user_id = stored_data["user_id"]
        
        # Determine actual platform for API calls (no longer needed for Instagram)
        actual_platform = platform
        
        try:
            # Check if this is a test code
            if code.startswith("test_code_"):
                # Generate mock token data for testing
                token_data = {
                    "access_token": f"mock_access_token_{platform}_{user_id}",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": f"mock_refresh_token_{platform}_{user_id}",
                    "scope": " ".join(PLATFORM_CONFIGS[platform]["scopes"])
                }
                
                # Mock profile data
                profile_data = {
                    "id": f"mock_{platform}_id_{user_id}",
                    "username": f"testuser_{platform}",
                    "name": f"Test User ({platform.title()})",
                    "email": f"testuser_{platform}@example.com" if platform != "twitter" else None,
                    "platform": platform
                }
            else:
                # Exchange code for access token
                code_verifier = stored_data.get("code_verifier") if platform == "twitter" else None
                token_data = await self._exchange_code_for_token(actual_platform, code, code_verifier)
                
                # Get user profile
                profile_data = await self._get_user_profile(actual_platform, token_data["access_token"])
            
            # Save social account
            social_account = await self._save_social_account(
                user_id=user_id,
                platform=platform,
                token_data=token_data,
                profile_data=profile_data
            )
            
            # Trigger data collection for the new account
            try:
                collection_result = await oauth_data_collector.collect_data_for_user(user_id)
                logger.info(f"Data collection completed for {platform}: {collection_result}")
            except Exception as e:
                logger.error(f"Data collection failed for {platform}: {e}")
            
            return {
                "success": True,
                "account_id": str(social_account.id),
                "platform": platform,
                "username": profile_data.get("username"),
                "display_name": profile_data.get("display_name")
            }
            
        except Exception as e:
            logger.error(f"OAuth callback failed for {platform}: {e}")
            raise Exception(f"Authentication failed: {str(e)}")
    
    async def _exchange_code_for_token(self, platform: str, code: str, code_verifier: Optional[str] = None) -> Dict:
        """Exchange authorization code for access token"""
        config = PLATFORM_CONFIGS[platform]
        
        client_secret_map = {
            "facebook": oauth_settings.FACEBOOK_CLIENT_SECRET,
            "instagram": oauth_settings.INSTAGRAM_CLIENT_SECRET,
            "reddit": oauth_settings.REDDIT_CLIENT_SECRET,
            "twitter": oauth_settings.TWITTER_CLIENT_SECRET,
        }
        
        client_id_map = {
            "facebook": oauth_settings.FACEBOOK_CLIENT_ID,
            "instagram": oauth_settings.INSTAGRAM_CLIENT_ID,
            "reddit": oauth_settings.REDDIT_CLIENT_ID,
            "twitter": oauth_settings.TWITTER_CLIENT_ID,
        }
        
        redirect_uri_map = {
            "facebook": oauth_settings.FACEBOOK_REDIRECT_URI,
            "instagram": oauth_settings.INSTAGRAM_REDIRECT_URI,
            "reddit": oauth_settings.REDDIT_REDIRECT_URI,
            "twitter": oauth_settings.TWITTER_REDIRECT_URI,
        }
        
        data = {
            "client_id": client_id_map[platform],
            "client_secret": client_secret_map[platform],
            "code": code,
            "redirect_uri": redirect_uri_map[platform],
            "grant_type": "authorization_code"
        }
        
        # Add code_verifier for PKCE (Twitter)
        if platform == "twitter" and code_verifier:
            data["code_verifier"] = code_verifier
        
        # Platform-specific headers and authentication
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        if platform == "reddit":
            # Reddit requires basic auth
            auth_string = f"{data['client_id']}:{data['client_secret']}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
            headers["User-Agent"] = "OSINT-Platform/1.0"
            data.pop("client_secret")
        elif platform == "twitter":
            # Twitter OAuth 2.0 requires basic auth
            auth_string = f"{data['client_id']}:{data['client_secret']}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
            data.pop("client_id")
            data.pop("client_secret")
        
        response = await self.http_client.post(
            config["token_url"],
            data=data,
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed for {platform}: {response.status_code} - {response.text}")
            raise Exception(f"Token exchange failed: {response.status_code}")
        
        token_data = response.json()
        
        # Validate required fields
        if "access_token" not in token_data:
            raise Exception("No access token received")
            
        return token_data
    
    async def _get_user_profile(self, platform: str, access_token: str) -> Dict:
        """Get user profile from platform"""
        config = PLATFORM_CONFIGS[platform]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Platform-specific headers
        if platform == "reddit":
            headers["User-Agent"] = "OSINT-Platform/1.0"
        
        # Platform-specific profile endpoints
        profile_endpoints = {
            "facebook": "/me?fields=id,name,email,picture.width(200).height(200)",
            "instagram": "/me?fields=id,username,name,account_type,media_count,followers_count,follows_count,biography,website,profile_picture_url",
            "reddit": "/api/v1/me",
            "twitter": "/2/users/me?user.fields=id,username,name,profile_image_url,public_metrics,verified,description,location"
        }
        
        endpoint = profile_endpoints[platform]
        url = f"{config['api_base']}{endpoint}"
        
        response = await self.http_client.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Profile fetch failed for {platform}: {response.status_code} - {response.text}")
            raise Exception(f"Profile fetch failed: {response.status_code}")
        
        profile_data = response.json()
        
        # Parse platform-specific profile data
        return self._parse_profile_data(platform, profile_data)
    
    def _parse_profile_data(self, platform: str, profile_data: Dict) -> Dict:
        """Parse platform-specific profile data into common format"""
        parsers = {
            "facebook": lambda d: {
                "user_id": d["id"],
                "username": d.get("name", ""),
                "display_name": d.get("name"),
                "email": d.get("email"),
                "profile_url": f"https://facebook.com/{d['id']}",
                "profile_picture": d.get("picture", {}).get("data", {}).get("url")
            },
            "instagram": lambda d: {
                "user_id": d["id"],
                "username": d.get("username", ""),
                "display_name": d.get("name", ""),
                "email": None,  # Instagram Basic Display API doesn't provide email
                "profile_url": f"https://instagram.com/{d.get('username', d['id'])}",
                "profile_picture": d.get("profile_picture_url")
            },
            "reddit": lambda d: {
                "user_id": d["id"],
                "username": d["name"],
                "display_name": d["name"],
                "email": d.get("email"),
                "profile_url": f"https://reddit.com/u/{d['name']}",
                "profile_picture": d.get("icon_img", "").replace("&amp;", "&") if d.get("icon_img") else None
            },
            "google": lambda d: {
                "user_id": d["items"][0]["id"] if d.get("items") else "",
                "username": d["items"][0]["snippet"]["title"] if d.get("items") else "",
                "display_name": d["items"][0]["snippet"]["title"] if d.get("items") else "",
                "profile_url": f"https://youtube.com/channel/{d['items'][0]['id']}" if d.get("items") else "",
                "profile_picture": d["items"][0]["snippet"]["thumbnails"]["default"]["url"] if d.get("items") and d["items"][0]["snippet"].get("thumbnails") else None
            },
            "twitter": lambda d: {
                "user_id": d["data"]["id"],
                "username": d["data"]["username"],
                "display_name": d["data"]["name"],
                "profile_url": f"https://twitter.com/{d['data']['username']}",
                "profile_picture": d["data"].get("profile_image_url")
            }
        }
        
        parser = parsers.get(platform)
        if not parser:
            raise ValueError(f"No parser available for {platform}")
            
        return parser(profile_data)
    
    async def _save_social_account(self, user_id: str, platform: str, token_data: Dict, profile_data: Dict) -> SocialAccount:
        """Save social account to database"""
        # Map OAuth platform names to PlatformType enum values
        platform_mapping = {}
        db_platform = platform_mapping.get(platform, platform.lower())
        
        # Calculate token expiration
        expires_at = None
        if "expires_in" in token_data:
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        
        # Check if account already exists
        existing_account = await SocialAccount.find_one(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == PlatformType(db_platform),
            SocialAccount.platform_user_id == profile_data["user_id"]
        )
        
        if existing_account:
            # Update existing account
            existing_account.access_token = token_data["access_token"]
            existing_account.refresh_token = token_data.get("refresh_token")
            existing_account.token_expires_at = expires_at
            existing_account.username = profile_data["username"]
            existing_account.display_name = profile_data["display_name"]
            existing_account.email = profile_data.get("email")
            existing_account.profile_picture = profile_data.get("profile_picture")
            existing_account.platform_data = token_data
            existing_account.is_active = True
            
            await existing_account.save()
            return existing_account
        
        # Create new account
        social_account = SocialAccount(
            user_id=user_id,
            platform=PlatformType(db_platform),
            platform_user_id=profile_data["user_id"],
            username=profile_data["username"],
            display_name=profile_data["display_name"],
            email=profile_data.get("email"),
            profile_url=profile_data.get("profile_url"),
            profile_picture=profile_data.get("profile_picture"),
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=expires_at,
            platform_data=token_data
        )
        
        await social_account.save()
        return social_account
    
    async def _store_oauth_state(self, state: str, user_id: str, platform: str, code_verifier: Optional[str] = None):
        """Store OAuth state for verification"""
        # Map OAuth platform names to PlatformType enum values
        platform_mapping = {
            "google": "youtube"
        }
        db_platform = platform_mapping.get(platform, platform.lower())
        
        expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry
        
        oauth_state = OAuthState(
            state=state,
            user_id=user_id,
            platform=PlatformType(db_platform),
            code_verifier=code_verifier,
            expires_at=expires_at
        )
        
        await oauth_state.save()
    
    async def _verify_oauth_state(self, state: str, platform: str) -> Optional[Dict]:
        """Verify OAuth state and return stored data"""
        # Map OAuth platform names to PlatformType enum values
        platform_mapping = {
            "google": "youtube"
        }
        db_platform = platform_mapping.get(platform, platform.lower())
        
        oauth_state = await OAuthState.find_one(
            OAuthState.state == state,
            OAuthState.platform == PlatformType(db_platform),
            OAuthState.is_used == False,
            OAuthState.expires_at > datetime.utcnow()
        )
        
        if not oauth_state:
            return None
        
        # Mark state as used
        oauth_state.is_used = True
        await oauth_state.save()
        
        return {
            "user_id": oauth_state.user_id,
            "platform": oauth_state.platform.value,
            "code_verifier": oauth_state.code_verifier
        }
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge from code verifier"""
        import hashlib
        import base64
        
        # Create SHA256 hash of the code verifier
        sha256 = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        
        # Base64url encode the hash
        code_challenge = base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')
        
        return code_challenge
    
    async def refresh_token(self, social_account: SocialAccount) -> bool:
        """Refresh access token for a social account"""
        if not social_account.refresh_token:
            return False
        
        platform = social_account.platform.value
        config = PLATFORM_CONFIGS[platform]
        
        # Platform-specific refresh logic
        if platform in ["facebook", "instagram"]:
            try:
                response = await self.http_client.post(
                    config["token_url"],
                    data={
                        "client_id": getattr(oauth_settings, f"{platform.upper()}_CLIENT_ID"),
                        "client_secret": getattr(oauth_settings, f"{platform.upper()}_CLIENT_SECRET"),
                        "refresh_token": social_account.refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    social_account.access_token = token_data["access_token"]
                    
                    if "expires_in" in token_data:
                        social_account.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
                    
                    await social_account.save()
                    return True
                    
            except Exception as e:
                logger.error(f"Token refresh failed for {platform}: {e}")
                
        return False

oauth_service = OAuthService()