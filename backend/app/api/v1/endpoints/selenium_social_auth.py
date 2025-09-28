"""
Social media authentication API endpoints - Selenium Browser Automation
No API limits - Unlimited users and data collection!
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
import logging
import asyncio
from datetime import datetime

from app.services.selenium_auth_service import selenium_service
from app.services.selenium_data_collector import DataCollectorFactory
from app.api.v1.endpoints.auth import get_current_user
from app.models.mongo_models import User
from app.models.social_auth_models import SocialAccount, CollectedPost, CollectedConnection
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/social-auth", tags=["Social Media Authentication - Selenium"])

# Supported platforms with unlimited data access
SUPPORTED_PLATFORMS = {
    "facebook": {
        "name": "Facebook",
        "data_types": ["posts", "friends", "profile", "photos", "interactions", "groups", "pages", "messages"],
        "unlimited": True,
        "description": "Complete access to your Facebook data including private posts and friends"
    },
    "instagram": {
        "name": "Instagram", 
        "data_types": ["posts", "stories", "followers", "following", "profile", "photos", "videos", "reels"],
        "unlimited": True,
        "description": "Full Instagram data including stories, followers, and private content"
    },
    "reddit": {
        "name": "Reddit",
        "data_types": ["posts", "comments", "subscriptions", "upvoted", "saved", "profile", "messages"],
        "unlimited": True,
        "description": "Complete Reddit history including saved posts and private messages"
    },
    "youtube": {
        "name": "YouTube",
        "data_types": ["videos", "subscriptions", "playlists", "comments", "likes", "history", "watch_later"],
        "unlimited": True,
        "description": "Full YouTube data including watch history and private playlists"
    },
    "twitter": {
        "name": "Twitter",
        "data_types": ["tweets", "following", "followers", "likes", "retweets", "lists", "messages", "bookmarks"],
        "unlimited": True,
        "description": "Complete Twitter data including DMs and private interactions"
    }
}

@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported social media platforms and unlimited data collection capabilities"""
    return {
        "platforms": SUPPORTED_PLATFORMS,
        "total_platforms": len(SUPPORTED_PLATFORMS),
        "message": "All platforms support unlimited users and data collection - No API limits!",
        "technology": "Selenium Browser Automation",
        "advantages": [
            "No API rate limits",
            "No developer app registration required",
            "Access to private data (friends, messages, etc.)",
            "Unlimited number of users",
            "No monthly API costs",
            "Works exactly like manual browsing"
        ]
    }

@router.post("/connect/{platform}")
async def initiate_browser_connection(
    platform: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Initiate browser automation connection to social media platform"""
    try:
        if platform.lower() not in SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=400, 
                detail=f"Platform {platform} not supported. Available: {list(SUPPORTED_PLATFORMS.keys())}"
            )
            
        # Check if user already has an active browser session
        browser_status = await selenium_service.get_browser_status(str(current_user.id))
        
        if browser_status.get("has_active_browser"):
            return {
                "success": False,
                "message": "You already have an active browser session. Please wait for it to complete or close your browser.",
                "status": "browser_active",
                "action_required": "Wait for current session to complete"
            }
        
        # Start browser authentication in background
        background_tasks.add_task(
            start_browser_authentication,
            user_id=str(current_user.id),
            platform=platform.lower(),
            username=current_user.username
        )
        
        logger.info(f"User {current_user.username} starting {platform} browser authentication")
        
        return {
            "success": True,
            "platform": platform,
            "status": "browser_opening",
            "message": f"Browser opening for {platform} login. Please complete login in the browser window.",
            "data_types": SUPPORTED_PLATFORMS[platform.lower()]["data_types"],
            "unlimited": True,
            "estimated_wait_time": "2-5 minutes",
            "instructions": [
                "1. Browser window will open automatically",
                "2. Log in to your account normally (username/password)",
                "3. Complete any 2FA/SMS verification if required", 
                "4. Browser will detect successful login automatically",
                "5. Browser closes and data collection starts in background",
                "6. You'll receive notifications when data collection is complete"
            ],
            "next_steps": [
                "Monitor the /status endpoint to check progress",
                "Use /collect endpoint to start data collection after login",
                "View collected data in the dashboard"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error initiating {platform} connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{platform}")
async def get_connection_status(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of browser authentication for a platform"""
    try:
        if platform.lower() not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
            
        # Check for existing social account
        account = await SocialAccount.find_one(
            SocialAccount.user_id == str(current_user.id),
            SocialAccount.platform == platform.lower()
        )
        
        browser_status = await selenium_service.get_browser_status(str(current_user.id))
        
        if account:
            return {
                "success": True,
                "platform": platform,
                "status": "connected",
                "connected_at": account.connected_at.isoformat() if account.connected_at else None,
                "username": account.username,
                "profile_data": account.profile_data,
                "has_active_browser": browser_status.get("has_active_browser", False),
                "data_available": {
                    "posts_count": await CollectedPost.count_documents({"user_id": str(current_user.id), "platform": platform.lower()}),
                    "connections_count": await CollectedConnection.count_documents({"user_id": str(current_user.id), "platform": platform.lower()})
                },
                "available_data_types": SUPPORTED_PLATFORMS[platform.lower()]["data_types"]
            }
        else:
            return {
                "success": False,
                "platform": platform,
                "status": "not_connected",
                "message": f"No {platform} account connected yet",
                "has_active_browser": browser_status.get("has_active_browser", False),
                "available_data_types": SUPPORTED_PLATFORMS[platform.lower()]["data_types"]
            }
            
    except Exception as e:
        logger.error(f"Error getting {platform} status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accounts")
async def get_connected_accounts(current_user: User = Depends(get_current_user)):
    """Get all connected social media accounts for user"""
    try:
        accounts = await SocialAccount.find(SocialAccount.user_id == str(current_user.id)).to_list()
        
        account_data = []
        for account in accounts:
            posts_count = await CollectedPost.count_documents({"user_id": str(current_user.id), "platform": account.platform})
            connections_count = await CollectedConnection.count_documents({"user_id": str(current_user.id), "platform": account.platform})
            
            account_data.append({
                "platform": account.platform,
                "username": account.username,
                "connected_at": account.connected_at.isoformat() if account.connected_at else None,
                "profile_data": account.profile_data,
                "posts_collected": posts_count,
                "connections_collected": connections_count,
                "available_data_types": SUPPORTED_PLATFORMS.get(account.platform, {}).get("data_types", [])
            })
            
        return {
            "success": True,
            "accounts": account_data,
            "total_accounts": len(account_data),
            "supported_platforms": list(SUPPORTED_PLATFORMS.keys()),
            "unlimited_collection": True
        }
        
    except Exception as e:
        logger.error(f"Error getting connected accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collect/{platform}")
async def start_data_collection(
    platform: str,
    background_tasks: BackgroundTasks,
    data_types: List[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Start data collection for a connected platform"""
    try:
        if platform.lower() not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
            
        # Check if account is connected
        account = await SocialAccount.find_one(
            SocialAccount.user_id == str(current_user.id),
            SocialAccount.platform == platform.lower()
        )
        
        if not account:
            raise HTTPException(
                status_code=404, 
                detail=f"No {platform} account connected. Please connect first using /connect/{platform}"
            )
            
        # Default to all available data types if none specified
        if not data_types:
            data_types = SUPPORTED_PLATFORMS[platform.lower()]["data_types"]
            
        # Validate data types
        available_types = SUPPORTED_PLATFORMS[platform.lower()]["data_types"]
        invalid_types = [dt for dt in data_types if dt not in available_types]
        if invalid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid data types: {invalid_types}. Available: {available_types}"
            )
            
        # Start data collection in background
        background_tasks.add_task(
            start_data_collection_task,
            user_id=str(current_user.id),
            platform=platform.lower(),
            data_types=data_types,
            account_username=account.username
        )
        
        logger.info(f"User {current_user.username} starting {platform} data collection: {data_types}")
        
        return {
            "success": True,
            "platform": platform,
            "status": "collection_started",
            "data_types": data_types,
            "unlimited": True,
            "message": f"Data collection started for {platform}. This may take 5-30 minutes depending on data size.",
            "estimated_time": "5-30 minutes",
            "what_happens_next": [
                "Browser automation will navigate through your account",
                "All specified data types will be collected",
                "Data is saved securely to your account",
                "You'll receive a notification when complete",
                "View progress in the dashboard"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error starting {platform} data collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/disconnect/{platform}")
async def disconnect_account(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """Disconnect and remove social media account"""
    try:
        if platform.lower() not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
            
        # Find and delete social account
        account = await SocialAccount.find_one(
            SocialAccount.user_id == str(current_user.id),
            SocialAccount.platform == platform.lower()
        )
        
        if not account:
            raise HTTPException(status_code=404, detail=f"No {platform} account connected")
            
        await account.delete()
        
        # Cleanup browser session if active
        await selenium_service.cleanup_driver(str(current_user.id))
        
        logger.info(f"User {current_user.username} disconnected {platform} account")
        
        return {
            "success": True,
            "platform": platform,
            "message": f"{platform} account disconnected successfully",
            "note": "Collected data is preserved. Reconnect anytime to collect new data."
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{platform}")
async def get_collected_data(
    platform: str,
    data_type: str = "posts",
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Get collected data for a platform"""
    try:
        if platform.lower() not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
            
        if data_type == "posts":
            posts = await CollectedPost.find(
                CollectedPost.user_id == str(current_user.id),
                CollectedPost.platform == platform.lower()
            ).skip(offset).limit(limit).to_list()
            
            return {
                "success": True,
                "platform": platform,
                "data_type": data_type,
                "data": [post.dict() for post in posts],
                "count": len(posts),
                "offset": offset,
                "limit": limit,
                "unlimited": True
            }
            
        elif data_type == "connections":
            connections = await CollectedConnection.find(
                CollectedConnection.user_id == str(current_user.id),
                CollectedConnection.platform == platform.lower()
            ).skip(offset).limit(limit).to_list()
            
            return {
                "success": True,
                "platform": platform,
                "data_type": data_type,
                "data": [conn.dict() for conn in connections],
                "count": len(connections),
                "offset": offset,
                "limit": limit,
                "unlimited": True
            }
        else:
            raise HTTPException(status_code=400, detail=f"Data type {data_type} not supported")
            
    except Exception as e:
        logger.error(f"Error getting {platform} data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions

async def start_browser_authentication(user_id: str, platform: str, username: str):
    """Background task to handle browser authentication"""
    try:
        logger.info("=" * 80)
        logger.info(f"🚀 BACKGROUND TASK STARTED: Browser authentication")
        logger.info(f"   User: {username} (ID: {user_id})")
        logger.info(f"   Platform: {platform}")
        logger.info("=" * 80)
        # Authenticate using Selenium
        logger.info(f"📱 Calling selenium_service.authenticate_platform...")
        result = await selenium_service.authenticate_platform(user_id, platform)
        logger.info(f"🔄 Authentication result: {result}")
        if result.get("status") == "success":
            account = SocialAccount(
                user_id=user_id,
                platform=platform,
                username=f"{platform}_user_{user_id[:8]}",  # Will be updated with real username during data collection
                connected_at=datetime.now(),
                profile_data={}
            )
            await account.insert()
            logger.info(f"Successfully authenticated {username} to {platform}")
        else:
            logger.error(f"Authentication failed for {username} on {platform}: {result}")
    except Exception as e:
        logger.error(f"Browser authentication error for {username} on {platform}: {e}", exc_info=True)
        logger.error("Browser will remain open for debugging. Close it manually when done.")
        return
    # Commented out cleanup for debugging so browser stays open
    # finally:
    #     await selenium_service.cleanup_driver(user_id)

async def start_data_collection_task(user_id: str, platform: str, data_types: List[str], account_username: str):
    """Background task to collect data using Selenium"""
    try:
        logger.info(f"Starting data collection for {account_username} on {platform}: {data_types}")
        
        # Create new browser session for data collection
        driver = selenium_service.create_browser_driver(user_id)
        
        # Load saved cookies to maintain session
        await selenium_service.load_cookies(driver, platform, user_id)
        
        # Create data collector
        collector = DataCollectorFactory.create_collector(platform, driver, user_id)
        
        # Collect data based on requested types
        for data_type in data_types:
            try:
                if data_type == "posts":
                    posts_data = await collector.collect_posts(max_posts=settings.SELENIUM_MAX_POSTS_PER_PLATFORM)
                    
                    # Save posts to database
                    for post_data in posts_data:
                        post = CollectedPost(**post_data)
                        await post.insert()
                        
                elif data_type == "friends" or data_type == "followers" or data_type == "following":
                    if platform == "facebook":
                        friends_data = await collector.collect_friends()
                    elif platform == "instagram":
                        friends_data = await collector.collect_followers()
                    elif platform == "twitter":
                        friends_data = await collector.collect_following()
                    else:
                        continue
                        
                    # Save connections to database
                    for friend_data in friends_data:
                        connection = CollectedConnection(**friend_data)
                        await connection.insert()
                        
                # Add more data types as needed
                logger.info(f"Completed collecting {data_type} for {account_username} on {platform}")
                
            except Exception as e:
                logger.error(f"Error collecting {data_type} for {platform}: {e}")
                
        logger.info(f"Data collection completed for {account_username} on {platform}")
        
    except Exception as e:
        logger.error(f"Data collection error for {platform}: {e}")
    finally:
        # Always cleanup browser resources
        await selenium_service.cleanup_driver(user_id)