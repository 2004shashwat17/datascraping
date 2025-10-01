"""
Dashboard endpoints for displaying analytics and statistics.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.mongo_models import User, PlatformEnum
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter()


class DashboardStats(BaseModel):
    total_posts: int
    active_threats: int
    trending_topics: int
    system_health: float
    last_updated: datetime


class ThreatAlert(BaseModel):
    id: str
    title: str
    platform: str
    time_ago: str
    severity: str
    confidence_score: float
    threat_type: str
    source_url: Optional[str] = None


class ActivityData(BaseModel):
    date: str
    posts: int
    threats: int
    trends: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get overall dashboard statistics."""
    
    # Return default stats since data collection models are removed
    return DashboardStats(
        total_posts=0,
        active_threats=0,
        trending_topics=0,
        system_health=100.0,
        last_updated=datetime.utcnow()
    )


@router.get("/threats", response_model=List[ThreatAlert])
async def get_threat_alerts(
    limit: int = 10, 
    current_user: User = Depends(get_current_user)
):
    """Get recent threat alerts for the user."""
    
    # Return empty list since threat detection models are removed
    return []


@router.get("/activity", response_model=List[ActivityData])
async def get_activity_trends(
    days: int = 7, 
    current_user: User = Depends(get_current_user)
):
    """Get activity trends for the past N days."""
    
    # Return empty activity data since data collection models are removed
    return []