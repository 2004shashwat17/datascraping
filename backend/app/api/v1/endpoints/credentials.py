"""
Credential-based data collection endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Dict, Optional
import logging

from app.services.credential_service import CredentialService
from app.core.security import get_current_user
from app.models.mongo_models import User

logger = logging.getLogger(__name__)

router = APIRouter()

class CredentialConnectRequest(BaseModel):
    """Request model for credential-based connection"""
    platform: str  # "instagram", "twitter", etc.
    email: EmailStr
    password: str
    target: Optional[str] = None  # username or hashtag to scrape (optional for comprehensive collection)
    max_posts: Optional[int] = 10
    api_token: Optional[str] = None  # For Apify

class ConnectResponse(BaseModel):
    """Response model for connection attempt"""
    success: bool
    message: str
    collected_posts: int = 0
    collected_followers: Optional[int] = None
    collected_following: Optional[int] = None
    platform: str
    target: Optional[str] = None
    error: Optional[str] = None

@router.post("/connect/credentials", response_model=ConnectResponse)
async def connect_with_credentials(
    request: CredentialConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Connect to social media platform using credentials and collect data
    """
    try:
        service = CredentialService()

        # Run collection in background to avoid timeout
        background_tasks.add_task(
            perform_collection,
            service=service,
            platform=request.platform,
            credentials={"email": request.email, "password": request.password, "api_token": request.api_token},
            target=request.target,
            max_posts=request.max_posts,
            user_id=str(current_user.id)
        )

        return ConnectResponse(
            success=True,
            message=f"Started collecting data from {request.platform} for target {request.target or 'self'}",
            collected_posts=0,  # Will be updated when collection completes
            platform=request.platform,
            target=request.target
        )

    except Exception as e:
        logger.error(f"Error initiating credential-based collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start collection: {str(e)}")

async def perform_collection(
    service: CredentialService,
    platform: str,
    credentials: Dict[str, str],
    target: str,
    max_posts: int,
    user_id: str
):
    """Background task to perform the actual data collection"""
    try:
        logger.info(f"Starting background collection for user {user_id}: {platform}/{target}")

        result = await service.collect_data(
            platform=platform,
            credentials=credentials,
            target=target,
            max_posts=max_posts
        )

        if result["success"]:
            collected_posts = result.get('collected_posts', 0)
            collected_followers = result.get('collected_followers', 0)
            collected_following = result.get('collected_following', 0)
            
            if collected_followers > 0 or collected_following > 0:
                logger.info(f"Successfully collected {collected_posts} posts, {collected_followers} followers, {collected_following} following from {platform}/{target}")
            else:
                logger.info(f"Successfully collected {collected_posts} posts from {platform}/{target}")
        else:
            logger.error(f"Failed to collect data from {platform}/{target}: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Background collection failed for {platform}/{target}: {e}")

@router.get("/connect/status")
async def get_collection_status(current_user: User = Depends(get_current_user)):
    """
    Get the status of ongoing collections
    """
    # For now, just return a placeholder
    # TODO: Implement proper status tracking with database
    return {
        "message": "Collection runs in background. Check backend logs for results.",
        "status": "Check backend console/logs for detailed collection results",
        "last_collection": "Unknown"
    }