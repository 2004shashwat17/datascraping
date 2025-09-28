"""
Data collection service for gathering social media data.
This service collects data and properly links it to users.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random
from beanie import PydanticObjectId

from app.models.mongo_models import (
    User, SocialMediaPost, ThreatDetection, 
    PlatformEnum, ThreatLevelEnum, SeverityEnum
)


class DataCollectorService:
    """Service for collecting social media data and analyzing threats."""
    
    def __init__(self):
        # Mock data for different platforms
        self.mock_posts = {
            PlatformEnum.FACEBOOK: [
                {
                    "post_id": "fb_123456",
                    "author": "SecurityNews",
                    "content": "New cybersecurity vulnerability discovered in popular software",
                    "url": "https://facebook.com/post/123456"
                },
                {
                    "post_id": "fb_789012", 
                    "author": "TechNews",
                    "content": "Company reports data breach affecting 100,000 users",
                    "url": "https://facebook.com/post/789012"
                }
            ],
            PlatformEnum.TWITTER: [
                {
                    "post_id": "tw_345678",
                    "author": "CyberAlert", 
                    "content": "BREAKING: Zero-day exploit found in critical infrastructure software #cybersecurity #vulnerability",
                    "url": "https://twitter.com/post/345678"
                },
                {
                    "post_id": "tw_901234",
                    "author": "HealthSec",
                    "content": "Ransomware attack hits major hospital network, patient data at risk", 
                    "url": "https://twitter.com/post/901234"
                }
            ],
            PlatformEnum.INSTAGRAM: [
                {
                    "post_id": "ig_567890",
                    "author": "CyberSecTips",
                    "content": "Infographic: How to protect yourself from phishing attacks",
                    "url": "https://instagram.com/p/567890"
                }
            ],
            PlatformEnum.YOUTUBE: [
                {
                    "post_id": "yt_123789",
                    "author": "TechSecChannel", 
                    "content": "How hackers exploit IoT devices - Security Analysis",
                    "url": "https://youtube.com/watch?v=123789"
                }
            ],
            PlatformEnum.REDDIT: [
                {
                    "post_id": "rd_456123",
                    "author": "SecurityResearcher",
                    "content": "New malware strain targeting financial institutions discovered",
                    "url": "https://reddit.com/r/cybersecurity/456123"
                }
            ]
        }
        
        # Threat detection keywords
        self.threat_keywords = {
            "vulnerability": {"type": "vulnerability", "base_score": 0.4},
            "exploit": {"type": "vulnerability", "base_score": 0.7},
            "zero-day": {"type": "vulnerability", "base_score": 1.0},
            "breach": {"type": "data_breach", "base_score": 0.5},
            "ransomware": {"type": "malware", "base_score": 0.7},
            "malware": {"type": "malware", "base_score": 0.6}, 
            "phishing": {"type": "phishing", "base_score": 0.4},
            "attack": {"type": "attack", "base_score": 0.3},
            "hacker": {"type": "attack", "base_score": 0.3},
            "cybersecurity": {"type": "vulnerability", "base_score": 0.2}
        }
    
    async def collect_data_for_user(self, user: User) -> Dict[str, Any]:
        """
        Collect social media data for a specific user.
        This ensures all collected data is properly linked to the user.
        """
        if not user.permissions_granted or not user.enabled_platforms:
            return {
                "status": "error",
                "message": "No platforms enabled for data collection",
                "posts_collected": 0,
                "threats_detected": 0
            }
        
        collected_posts = []
        detected_threats = []
        
        # Collect data from each enabled platform
        for platform in user.enabled_platforms:
            platform_posts = await self._collect_platform_data(platform, user)
            collected_posts.extend(platform_posts)
            
            # Analyze threats for each post
            for post in platform_posts:
                threats = await self._analyze_threats(post, user)
                detected_threats.extend(threats)
        
        return {
            "status": "success",
            "message": f"Data collection completed for user {user.username}",
            "posts_collected": len(collected_posts),
            "threats_detected": len(detected_threats),
            "platforms": [p.value for p in user.enabled_platforms],
            "user_id": str(user.id)
        }
    
    async def _collect_platform_data(self, platform: PlatformEnum, user: User) -> List[SocialMediaPost]:
        """Collect data from a specific platform for a user."""
        posts = []
        mock_data = self.mock_posts.get(platform, [])
        
        for post_data in mock_data:
            # Create unique post_id for this user to avoid conflicts
            unique_post_id = f"{post_data['post_id']}_{str(user.id)[-6:]}"
            
            # Check if we already collected this post for this user
            existing_post = await SocialMediaPost.find_one(
                SocialMediaPost.post_id == unique_post_id,
                SocialMediaPost.collected_by == user.id
            )
            
            if existing_post:
                continue  # Skip if already collected
            
            # Create new post linked to this user
            post = SocialMediaPost(
                platform=platform,
                post_id=unique_post_id,
                author=post_data["author"],
                content=post_data["content"],
                url=post_data["url"],
                posted_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                collected_at=datetime.utcnow(),
                collected_by=user.id,  # 🔑 THIS IS THE KEY - Link to user!
                engagement_metrics={
                    "likes": random.randint(10, 1000),
                    "shares": random.randint(1, 100),
                    "comments": random.randint(0, 50)
                },
                likes_count=random.randint(10, 1000),
                shares_count=random.randint(1, 100),
                comments_count=random.randint(0, 50)
            )
            
            await post.save()
            posts.append(post)
        
        return posts
    
    async def _analyze_threats(self, post: SocialMediaPost, user: User) -> List[ThreatDetection]:
        """Analyze a post for potential threats and link to user."""
        threats = []
        content_lower = post.content.lower()
        
        matched_keywords = []
        total_score = 0.0
        threat_types = set()
        
        # Check for threat keywords
        for keyword, threat_info in self.threat_keywords.items():
            if keyword in content_lower:
                matched_keywords.append(keyword)
                total_score += threat_info["base_score"]
                threat_types.add(threat_info["type"])
        
        # Create threat detection for each type found
        for threat_type in threat_types:
            confidence_score = min(total_score, 1.0)  # Cap at 1.0
            
            # Determine severity based on confidence
            if confidence_score >= 0.8:
                severity = "critical"
            elif confidence_score >= 0.6:
                severity = "high"
            elif confidence_score >= 0.3:
                severity = "medium"
            else:
                severity = "low"
            
            threat = ThreatDetection(
                platform=post.platform,
                post_id=str(post.id),
                threat_type=threat_type,
                confidence_score=confidence_score,
                severity=severity,
                description=f"Potential {severity} threat detected in {post.platform.value} post",
                detection_method="keyword_matching",
                detected_at=datetime.utcnow(),
                detected_by=user.id,  # 🔑 Link threat to user!
                keywords_matched=matched_keywords,
                source_url=post.url
            )
            
            await threat.save()
            threats.append(threat)
        
        return threats


# Create singleton instance
data_collector = DataCollectorService()