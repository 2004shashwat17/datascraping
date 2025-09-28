"""
MongoDB database configuration and connection management for the OSINT platform.
Uses Motor (async MongoDB driver) and Beanie ODM for document modeling.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import logging
from typing import Optional
from app.core.config import get_settings
from app.models.mongo_models import SocialMediaPost, User, ThreatDetection, TrendAnalysis
from app.models.social_auth_models import (
    SocialAccount, 
    CollectedPost, 
    CollectedConnection, 
    CollectedInteraction,
    DataCollectionJob,
    OAuthState
)

logger = logging.getLogger(__name__)
settings = get_settings()


class MongoDB:
    """MongoDB connection manager"""
    client: Optional[AsyncIOMotorClient] = None
    database = None


mongodb = MongoDB()


async def connect_to_mongo():
    """Create database connection with fallback options"""
    connection_attempts = [
        # Attempt 1: Standard Atlas connection with TLS
        {
            "url": settings.database_url,
            "options": {
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 10000,
                "socketTimeoutMS": 10000,
                "maxPoolSize": 10,
                "minPoolSize": 1,
                "tls": True,
                "tlsAllowInvalidCertificates": False,
                "retryWrites": True
            }
        },
        # Attempt 2: Atlas connection with relaxed SSL
        {
            "url": settings.database_url,
            "options": {
                "serverSelectionTimeoutMS": 15000,
                "connectTimeoutMS": 15000,
                "socketTimeoutMS": 15000,
                "maxPoolSize": 5,
                "minPoolSize": 1,
                "tls": True,
                "tlsAllowInvalidCertificates": True,  # More permissive for SSL issues
                "retryWrites": True
            }
        },
        # Attempt 3: Local MongoDB fallback
        {
            "url": "mongodb://localhost:27017/osint_platform",
            "options": {
                "serverSelectionTimeoutMS": 5000,
                "connectTimeoutMS": 5000,
                "socketTimeoutMS": 5000,
                "maxPoolSize": 5,
                "minPoolSize": 1
            }
        }
    ]
    
    for i, attempt in enumerate(connection_attempts):
        try:
            logger.info(f"Connection attempt {i+1}/{len(connection_attempts)}")
            
            # Create motor client
            mongodb.client = AsyncIOMotorClient(attempt["url"], **attempt["options"])
            
            # Get database
            mongodb.database = mongodb.client[settings.db_name if hasattr(settings, 'db_name') else 'osint_platform']
            
            # Test connection
            logger.info(f"Testing MongoDB connection to: {attempt['url'][:50]}...")
            await mongodb.client.admin.command('ping')
            
            logger.info(f"✅ Connected to MongoDB: {settings.db_name if hasattr(settings, 'db_name') else 'osint_platform'} (Attempt {i+1})")
            
            # Initialize Beanie ODM
            logger.info("Initializing Beanie ODM...")
            try:
                await init_beanie(
                    database=mongodb.database,
                    document_models=[
                        SocialMediaPost,
                        User,
                        ThreatDetection,
                        TrendAnalysis,
                        SocialAccount,
                        CollectedPost,
                        CollectedConnection,
                        CollectedInteraction,
                        DataCollectionJob,
                        OAuthState,
                    ]
                )
                logger.info("✅ Beanie ODM initialized successfully")
            except Exception as beanie_error:
                logger.error(f"❌ Beanie ODM initialization failed: {beanie_error}")
                raise
            
            return True
            
        except Exception as e:
            logger.warning(f"Connection attempt {i+1} failed: {type(e).__name__}: {str(e)}")
            if mongodb.client:
                mongodb.client.close()
                mongodb.client = None
            
            if i == len(connection_attempts) - 1:
                # All attempts failed
                logger.error(f"❌ Failed to connect to MongoDB after {len(connection_attempts)} attempts: {type(e).__name__}: {str(e)}")
                logger.error(f"Connection URL (partial): {settings.database_url[:50] if hasattr(settings, 'database_url') else 'Not set'}...")
                return False
            continue
    
    return False


async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Disconnected from MongoDB")


def get_database():
    """Get database instance"""
    return mongodb.database


async def ping_database():
    """Check database connection"""
    try:
        if mongodb.client:
            await mongodb.client.admin.command('ping')
            return True
        return False
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return False


# Dependency for FastAPI
async def get_mongo_db():
    """FastAPI dependency to get database"""
    return mongodb.database