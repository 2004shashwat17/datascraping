"""
OAuth endpoints for social media platform authentication
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from typing import Optional
import logging

from app.services.oauth_service import OAuthService
from app.core.security import get_current_user
from app.models.mongo_models import User
from app.models.social_auth_models import SocialAccount, PlatformType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["OAuth Authentication"])
oauth_service = OAuthService()


@router.get("/connect/{platform}")
async def connect_platform(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """Initiate OAuth flow for a social media platform"""
    try:
        auth_url, state = await oauth_service.get_authorization_url(platform, str(current_user.id))
        return {
            "auth_url": auth_url,
            "state": state
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None)
):
    """Handle OAuth callback from social media platform"""
    if error:
        logger.error(f"OAuth error for {platform}: {error}")
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"http://localhost:3000/social-accounts?error={error}&platform={platform}",
            status_code=302
        )

    try:
        result = await oauth_service.handle_callback(platform, code, state)

        # Redirect to frontend with success
        return RedirectResponse(
            url=f"http://localhost:3000/social-accounts?success=true&platform={platform}&account_id={result['account_id']}",
            status_code=302
        )

    except Exception as e:
        logger.error(f"OAuth callback failed for {platform}: {e}")
        return RedirectResponse(
            url=f"http://localhost:3000/social-accounts?error={str(e)}&platform={platform}",
            status_code=302
        )


@router.get("/accounts")
async def get_connected_accounts(current_user: User = Depends(get_current_user)):
    """Get user's connected social media accounts"""
    accounts = await SocialAccount.find(SocialAccount.user_id == str(current_user.id)).to_list()
    
    return {
        "accounts": [
            {
                "id": str(account.id),
                "user_id": account.user_id,
                "platform": account.platform.value.lower(),
                "platform_user_id": account.platform_user_id,
                "username": account.username,
                "display_name": account.display_name,
                "email": account.email,
                "profile_url": account.profile_url,
                "profile_picture": account.profile_picture,
                "connected_at": account.connected_at.isoformat(),
                "last_sync": account.last_sync.isoformat() if account.last_sync else None,
                "is_active": account.is_active,
                "collect_posts": account.collect_posts,
                "collect_connections": account.collect_connections,
                "collect_interactions": account.collect_interactions,
            }
            for account in accounts
        ]
    }


@router.delete("/disconnect/{platform}")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """Disconnect a social media platform"""
    try:
        # Map OAuth platform names to PlatformType enum values
        platform_mapping = {
            "google": "youtube"
        }
        db_platform = platform_mapping.get(platform, platform.lower())
        
        # Find and delete the social account
        account = await SocialAccount.find_one(
            SocialAccount.user_id == str(current_user.id),
            SocialAccount.platform == PlatformType(db_platform)
        )
        
        if not account:
            raise HTTPException(status_code=404, detail=f"No {platform} account connected")
        
        await account.delete()
        
        return {"message": f"Successfully disconnected {platform} account"}
        
    except Exception as e:
        logger.error(f"Error disconnecting {platform}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect {platform}")