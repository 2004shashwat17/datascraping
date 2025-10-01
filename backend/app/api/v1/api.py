"""
API v1 router module that aggregates all API endpoints.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import posts_mongo, auth, dashboard, oauth, credentials, twitter

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    posts_mongo.router,
    prefix="/posts",
    tags=["Social Media Posts"]
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)

api_router.include_router(
    oauth.router,
    tags=["OAuth Authentication"]
)

api_router.include_router(
    credentials.router,
    prefix="/collect",
    tags=["Credential-based Collection"]
)

api_router.include_router(
    twitter.router,
    tags=["Twitter API IO"]
)

# TODO: Add other endpoint routers when implemented:
# - threats: Threat detection endpoints
# - analysis: Data analysis endpoints  
# - users: User management endpoints