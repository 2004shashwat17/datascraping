"""
No-API Data Collector - Collects real security data without requiring API keys
Uses RSS feeds, public APIs, and web scraping for immediate testing
"""

import asyncio
import aiohttp
import feedparser
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from app.models.mongo_models import User, SocialMediaPost, ThreatDetection, PlatformEnum, ThreatLevelEnum
import hashlib

logger = logging.getLogger(__name__)

class NoAPIDataCollector:
    """Collect real security data without API keys"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def collect_data_for_user(self, user: User) -> Dict[str, Any]:
        """Collect real security data for a specific user from public sources"""
        
        if not user.permissions_granted or not user.enabled_platforms:
            return {"error": "No platforms enabled for data collection"}
        
        collected_posts = []
        detected_threats = []
        
        # User-specific identifier for personalized data
        user_hash = hashlib.md5(f"{user.username}_{user.id}".encode()).hexdigest()[:8]
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Collect from different sources based on enabled platforms
            if PlatformEnum.TWITTER in user.enabled_platforms:
                posts = await self._collect_hackernews_data(user, user_hash, "twitter")
                collected_posts.extend(posts)
            
            if PlatformEnum.REDDIT in user.enabled_platforms:
                posts = await self._collect_reddit_json_data(user, user_hash)
                collected_posts.extend(posts)
                
            if PlatformEnum.FACEBOOK in user.enabled_platforms:
                posts = await self._collect_security_rss_data(user, user_hash, "facebook")
                collected_posts.extend(posts)
                
            if PlatformEnum.YOUTUBE in user.enabled_platforms:
                posts = await self._collect_cve_data(user, user_hash, "youtube")
                collected_posts.extend(posts)
                
            if PlatformEnum.INSTAGRAM in user.enabled_platforms:
                posts = await self._collect_security_news_data(user, user_hash, "instagram")
                collected_posts.extend(posts)
        
        # Save all posts and analyze threats
        for post_data in collected_posts:
            try:
                post = SocialMediaPost(**post_data)
                await post.save()
                
                # Analyze for threats
                threats = await self._analyze_post_for_threats(post, user)
                for threat_data in threats:
                    threat = ThreatDetection(**threat_data)
                    await threat.save()
                    detected_threats.append(threat)
                    
            except Exception as e:
                logger.error(f"Error saving post: {e}")
        
        return {
            "status": "completed",
            "user_id": str(user.id),
            "username": user.username,
            "collected_posts": len(collected_posts),
            "detected_threats": len(detected_threats),
            "platforms": [p.value for p in user.enabled_platforms],
            "data_sources": ["hackernews", "reddit_public", "security_rss", "cve_database"]
        }
    
    async def _collect_hackernews_data(self, user: User, user_hash: str, platform: str) -> List[Dict[str, Any]]:
        """Collect from HackerNews API (no auth required)"""
        posts = []
        
        try:
            # Get top stories
            async with self.session.get("https://hacker-news.firebaseio.com/v0/topstories.json") as response:
                if response.status == 200:
                    story_ids = await response.json()
                    
                    # Get first 5 stories
                    for story_id in story_ids[:5]:
                        async with self.session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json") as story_response:
                            if story_response.status == 200:
                                story = await story_response.json()
                                
                                if story and "title" in story:
                                    post = {
                                        "platform": PlatformEnum(platform),
                                        "post_id": f"{platform}_{user_hash}_{story_id}",
                                        "content": f"[{user.username} monitored] {story['title']} - {story.get('text', '')}",
                                        "author": story.get("by", "hackernews"),
                                        "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                        "posted_at": datetime.fromtimestamp(story.get("time", 0)),
                                        "collected_at": datetime.utcnow(),
                                        "collected_by": user.id,
                                        "engagement_metrics": {"score": story.get("score", 0)},
                                        "likes_count": story.get("score", 0),
                                        "comments_count": story.get("descendants", 0)
                                    }
                                    posts.append(post)
                                    
        except Exception as e:
            logger.error(f"HackerNews collection error: {e}")
            
        return posts
    
    async def _collect_reddit_json_data(self, user: User, user_hash: str) -> List[Dict[str, Any]]:
        """Collect from Reddit public JSON (no auth required)"""
        posts = []
        
        # Security-related subreddits
        subreddits = ["cybersecurity", "netsec", "security"]
        
        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=3"
                headers = {"User-Agent": f"OSINT-Platform-{user.username}/1.0"}
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get("data", {}).get("children", []):
                            post_data = item["data"]
                            
                            post = {
                                "platform": PlatformEnum.REDDIT,
                                "post_id": f"reddit_{user_hash}_{post_data['id']}",
                                "content": f"[{user.username} security feed] {post_data.get('title', '')} - {post_data.get('selftext', '')[:200]}",
                                "author": post_data.get("author", "unknown"),
                                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                "posted_at": datetime.fromtimestamp(post_data.get("created_utc", 0)),
                                "collected_at": datetime.utcnow(),
                                "collected_by": user.id,
                                "engagement_metrics": {"score": post_data.get("score", 0)},
                                "likes_count": post_data.get("ups", 0),
                                "comments_count": post_data.get("num_comments", 0)
                            }
                            posts.append(post)
                            
            except Exception as e:
                logger.error(f"Reddit collection error for r/{subreddit}: {e}")
                
        return posts
    
    async def _collect_security_rss_data(self, user: User, user_hash: str, platform: str) -> List[Dict[str, Any]]:
        """Collect from security RSS feeds"""
        posts = []
        
        # Security RSS feeds
        rss_feeds = [
            "https://feeds.feedburner.com/eset/blog",
            "https://www.schneier.com/blog/atom.xml",
            "https://krebsonsecurity.com/feed/"
        ]
        
        for feed_url in rss_feeds:
            try:
                async with self.session.get(feed_url) as response:
                    if response.status == 200:
                        feed_content = await response.text()
                        feed = feedparser.parse(feed_content)
                        
                        for entry in feed.entries[:2]:  # Limit to 2 per feed
                            post_id = hashlib.md5(f"{entry.link}_{user_hash}".encode()).hexdigest()[:12]
                            
                            post = {
                                "platform": PlatformEnum(platform),
                                "post_id": f"{platform}_{user_hash}_{post_id}",
                                "content": f"[{user.username} security news] {entry.title} - {entry.get('summary', '')[:200]}",
                                "author": feed.feed.get("title", "Security News"),
                                "url": entry.link,
                                "posted_at": datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.utcnow(),
                                "collected_at": datetime.utcnow(),
                                "collected_by": user.id,
                                "engagement_metrics": {},
                                "likes_count": 0,
                                "comments_count": 0
                            }
                            posts.append(post)
                            
            except Exception as e:
                logger.error(f"RSS collection error for {feed_url}: {e}")
                
        return posts
    
    async def _collect_cve_data(self, user: User, user_hash: str, platform: str) -> List[Dict[str, Any]]:
        """Collect from CVE database (public API)"""
        posts = []
        
        try:
            # NIST CVE API
            url = "https://services.nvd.nist.gov/rest/json/cves/1.0"
            params = {
                "resultsPerPage": 5,
                "startIndex": 0
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for cve in data.get("result", {}).get("CVE_Items", []):
                        cve_data = cve["cve"]
                        cve_id = cve_data["CVE_data_meta"]["ID"]
                        
                        description = ""
                        if cve_data.get("description", {}).get("description_data"):
                            description = cve_data["description"]["description_data"][0].get("value", "")
                        
                        post = {
                            "platform": PlatformEnum(platform),
                            "post_id": f"{platform}_{user_hash}_{cve_id}",
                            "content": f"[{user.username} CVE monitor] {cve_id}: {description[:300]}",
                            "author": "NIST NVD",
                            "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                            "posted_at": datetime.utcnow() - timedelta(hours=1),  # Recent
                            "collected_at": datetime.utcnow(),
                            "collected_by": user.id,
                            "engagement_metrics": {"severity": "high"},
                            "likes_count": 0,
                            "comments_count": 0
                        }
                        posts.append(post)
                        
        except Exception as e:
            logger.error(f"CVE collection error: {e}")
            
        return posts
    
    async def _collect_security_news_data(self, user: User, user_hash: str, platform: str) -> List[Dict[str, Any]]:
        """Collect from security news APIs"""
        posts = []
        
        try:
            # Alternative free news source
            url = "https://hn.algolia.com/api/v1/search"
            params = {
                "query": "cybersecurity vulnerability breach",
                "hitsPerPage": 3
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for hit in data.get("hits", []):
                        post_id = f"{platform}_{user_hash}_{hit.get('objectID', '')}"
                        
                        post = {
                            "platform": PlatformEnum(platform),
                            "post_id": post_id,
                            "content": f"[{user.username} news alert] {hit.get('title', '')} - {hit.get('comment_text', '')}",
                            "author": hit.get("author", "Security News"),
                            "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                            "posted_at": datetime.fromisoformat(hit["created_at"].replace("Z", "+00:00")) if hit.get("created_at") else datetime.utcnow(),
                            "collected_at": datetime.utcnow(),
                            "collected_by": user.id,
                            "engagement_metrics": {"points": hit.get("points", 0)},
                            "likes_count": hit.get("points", 0),
                            "comments_count": hit.get("num_comments", 0)
                        }
                        posts.append(post)
                        
        except Exception as e:
            logger.error(f"Security news collection error: {e}")
            
        return posts
    
    async def _analyze_post_for_threats(self, post: SocialMediaPost, user: User) -> List[Dict[str, Any]]:
        """Analyze collected post for potential threats"""
        
        threats = []
        content = post.content.lower()
        
        # Enhanced threat detection keywords
        threat_patterns = {
            "vulnerability": {
                "keywords": ["vulnerability", "exploit", "zero-day", "cve-", "security flaw", "bug", "patch"],
                "severity": "high"
            },
            "malware": {
                "keywords": ["malware", "virus", "trojan", "ransomware", "botnet", "backdoor", "rootkit"],
                "severity": "critical"
            },
            "phishing": {
                "keywords": ["phishing", "scam", "fake login", "suspicious link", "credential theft"],
                "severity": "medium"
            },
            "data_breach": {
                "keywords": ["data breach", "leaked", "compromised", "stolen data", "exposed database"],
                "severity": "high"
            },
            "network_attack": {
                "keywords": ["ddos", "denial of service", "attack", "intrusion", "unauthorized access"],
                "severity": "medium"
            }
        }
        
        for threat_type, pattern in threat_patterns.items():
            matched_keywords = [kw for kw in pattern["keywords"] if kw in content]
            
            if matched_keywords:
                confidence = min(len(matched_keywords) / len(pattern["keywords"]), 1.0)
                
                threat = {
                    "platform": post.platform,
                    "post_id": str(post.id),
                    "threat_type": threat_type,
                    "confidence_score": confidence,
                    "severity": pattern["severity"],
                    "description": f"Detected {threat_type} indicators for user {user.username}",
                    "detected_at": datetime.utcnow(),
                    "detected_by": user.id,
                    "keywords_matched": matched_keywords,
                    "source_url": post.url
                }
                threats.append(threat)
        
        return threats

# Create singleton instance  
no_api_collector = NoAPIDataCollector()