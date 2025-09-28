"""
Dashboard endpoints for displaying analytics and statistics.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.mongo_models import User, SocialMediaPost, ThreatDetection, PlatformEnum
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
    
    try:
        # Count total posts collected by this user
        try:
            total_posts = await SocialMediaPost.find(
                SocialMediaPost.collected_by == current_user.id
            ).count()
        except AttributeError:
            # Fallback to dictionary query
            total_posts = await SocialMediaPost.find(
                {"collected_by": current_user.id}
            ).count()
    except Exception as e:
        print(f"Error counting posts: {e}")
        total_posts = 0
    
    # Count active threats (detected in last 24 hours)
    try:
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        try:
            active_threats = await ThreatDetection.find(
                ThreatDetection.detected_by == current_user.id,
                ThreatDetection.detected_at >= twenty_four_hours_ago,
                ThreatDetection.is_confirmed != True  # Include unconfirmed and non-false-positives
            ).count()
        except AttributeError:
            # Fallback to dictionary query
            active_threats = await ThreatDetection.find({
                "detected_by": current_user.id,
                "detected_at": {"$gte": twenty_four_hours_ago},
                "is_confirmed": {"$ne": True}
            }).count()
    except Exception as e:
        print(f"Error counting threats: {e}")
        active_threats = 0
    
    # Count trending topics (posts with high engagement in last 24 hours)
    try:
        try:
            trending_posts = await SocialMediaPost.find(
                SocialMediaPost.collected_by == current_user.id,
                SocialMediaPost.collected_at >= twenty_four_hours_ago
            ).to_list()
        except AttributeError:
            # Fallback to dictionary query
            trending_posts = await SocialMediaPost.find({
                "collected_by": current_user.id,
                "collected_at": {"$gte": twenty_four_hours_ago}
            }).to_list()
        
        # Simple trending calculation based on engagement
        trending_topics = 0
        for post in trending_posts:
            if post.engagement_metrics:
                total_engagement = sum(post.engagement_metrics.values())
                if total_engagement > 100:  # Threshold for trending
                    trending_topics += 1
    except Exception as e:
        print(f"Error counting trending topics: {e}")
        trending_topics = 0
    
    # System health (mock calculation)
    enabled_platforms = len(current_user.enabled_platforms) if current_user.enabled_platforms else 0
    max_platforms = 5
    system_health = (enabled_platforms / max_platforms) * 100 if max_platforms > 0 else 0
    
    return DashboardStats(
        total_posts=total_posts,
        active_threats=active_threats,
        trending_topics=trending_topics,
        system_health=system_health,
        last_updated=datetime.utcnow()
    )


@router.get("/threats", response_model=List[ThreatAlert])
async def get_threat_alerts(
    limit: int = 10, 
    current_user: User = Depends(get_current_user)
):
    """Get recent threat alerts for the user."""
    
    try:
        # Try modern Beanie query syntax first
        threats = await ThreatDetection.find(
            ThreatDetection.detected_by == current_user.id,
            ThreatDetection.is_confirmed != True  # Exclude confirmed false positives
        ).sort(-ThreatDetection.detected_at).limit(limit).to_list()
    except AttributeError:
        # Fallback to dictionary-based queries if attributes don't work
        threats = await ThreatDetection.find(
            {"detected_by": current_user.id, "is_confirmed": {"$ne": True}}
        ).sort([("detected_at", -1)]).limit(limit).to_list()
    
    alerts = []
    for threat in threats:
        # Calculate time ago
        time_diff = datetime.utcnow() - threat.detected_at
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} min ago"
        else:
            time_ago = "Just now"
        
        alerts.append(ThreatAlert(
            id=str(threat.id),
            title=threat.description,
            platform=threat.platform.value.title(),
            time_ago=time_ago,
            severity=threat.severity.title(),
            confidence_score=threat.confidence_score,
            threat_type=threat.threat_type,
            source_url=threat.source_url
        ))
    
    return alerts


@router.get("/activity", response_model=List[ActivityData])
async def get_activity_trends(
    days: int = 7, 
    current_user: User = Depends(get_current_user)
):
    """Get activity trends for the past N days."""
    
    activity_data = []
    
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        # Count posts for this day
        try:
            posts_count = await SocialMediaPost.find(
                SocialMediaPost.collected_by == current_user.id,
                SocialMediaPost.collected_at >= date_start,
                SocialMediaPost.collected_at < date_end
            ).count()
        except AttributeError:
            posts_count = await SocialMediaPost.find({
                "collected_by": current_user.id,
                "collected_at": {"$gte": date_start, "$lt": date_end}
            }).count()
        
        # Count threats for this day
        try:
            threats_count = await ThreatDetection.find(
                ThreatDetection.detected_by == current_user.id,
                ThreatDetection.detected_at >= date_start,
                ThreatDetection.detected_at < date_end
            ).count()
        except AttributeError:
            threats_count = await ThreatDetection.find({
                "detected_by": current_user.id,
                "detected_at": {"$gte": date_start, "$lt": date_end}
            }).count()
        
        # Count trending topics (simplified)
        try:
            trending_posts = await SocialMediaPost.find(
                SocialMediaPost.collected_by == current_user.id,
                SocialMediaPost.collected_at >= date_start,
                SocialMediaPost.collected_at < date_end
            ).to_list()
        except AttributeError:
            trending_posts = await SocialMediaPost.find({
                "collected_by": current_user.id,
                "collected_at": {"$gte": date_start, "$lt": date_end}
            }).to_list()
        
        trends_count = 0
        for post in trending_posts:
            if post.engagement_metrics:
                total_engagement = sum(post.engagement_metrics.values())
                if total_engagement > 50:  # Lower threshold for daily trends
                    trends_count += 1
        
        activity_data.append(ActivityData(
            date=date.strftime("%Y-%m-%d"),
            posts=posts_count,
            threats=threats_count,
            trends=trends_count
        ))
    
    # Reverse to show oldest first (for chart display)
    return list(reversed(activity_data))