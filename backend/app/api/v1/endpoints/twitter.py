"""
Twitter API IO endpoints for credential-based data collection
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.twitter_api_io_collector import TwitterApiIOCollector
from app.core.config import get_settings
from app.core.mongodb import get_database
from app.models.mongo_models import User
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twitter", tags=["Twitter API IO"])

class TwitterConnectRequest(BaseModel):
    username: str
    max_posts: int = 10

class TwitterConnectResponse(BaseModel):
    success: bool
    message: str
    username: str
    posts_collected: int

@router.post("/connect/credentials", response_model=TwitterConnectResponse)
async def connect_twitter_credentials(
    request: TwitterConnectRequest,
    current_user: User = Depends(get_current_user)
):
    """Connect to Twitter using username and collect data via TwitterApiIO"""
    try:
        settings = get_settings()

        if not settings.twitter_api_io_key:
            raise HTTPException(
                status_code=500,
                detail="TwitterApiIO API key not configured"
            )

        # Initialize TwitterApiIO collector
        async with TwitterApiIOCollector(settings.twitter_api_io_key) as collector:
            # Collect and save data
            posts_collected = await collector.collect_and_save(
                platform="twitter",
                target=request.username,
                max_posts=request.max_posts
            )

        logger.info(f"Successfully collected {posts_collected} posts for Twitter user {request.username}")

        return TwitterConnectResponse(
            success=True,
            message=f"Successfully connected to Twitter account @{request.username}",
            username=request.username,
            posts_collected=posts_collected
        )

    except Exception as e:
        logger.error(f"Error connecting to Twitter: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Twitter: {str(e)}"
        )

@router.get("/test")
async def test_twitter_api():
    """Test TwitterApiIO connection"""
    try:
        settings = get_settings()

        if not settings.twitter_api_io_key:
            return {"error": "TwitterApiIO API key not configured"}

        async with TwitterApiIOCollector(settings.twitter_api_io_key) as collector:
            # Test with a known public account
            profile = await collector.get_user_profile("twitter")

            if profile:
                return {
                    "success": True,
                    "message": "TwitterApiIO connection successful",
                    "test_profile": profile
                }
            else:
                return {"error": "Failed to fetch test profile"}

    except Exception as e:
        return {"error": f"TwitterApiIO test failed: {str(e)}"}

@router.get("/data/{username}")
async def get_collected_twitter_data(username: str, current_user: User = Depends(get_current_user)):
    """Get collected Twitter data for a specific username"""
    try:
        from app.models.mongo_models import SocialMediaPost, PlatformEnum
        
        # Get posts from database
        posts = await SocialMediaPost.find(
            SocialMediaPost.author_username == username,
            SocialMediaPost.platform == PlatformEnum.TWITTER
        ).sort(-SocialMediaPost.created_at).to_list()
        
        return {
            "username": username,
            "total_posts": len(posts),
            "posts": [
                {
                    "id": str(post.id),
                    "content": post.content,
                    "created_at": post.created_at.isoformat() if post.created_at else None,
                    "engagement_metrics": post.engagement_metrics,
                    "platform_id": post.platform_id,
                    "collected_at": post.metadata.get("collected_at") if post.metadata else None
                }
                for post in posts[:10]  # Return latest 10 posts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving Twitter data for {username}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Twitter data: {str(e)}"
        )