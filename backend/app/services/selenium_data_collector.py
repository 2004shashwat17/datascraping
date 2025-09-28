"""
Selenium Data Collectors for Social Media Platforms
Extracts posts, friends, interactions, search history, and more!
"""

import asyncio
import json
import re
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from app.core.config import get_settings
from app.models.social_auth_models import CollectedPost, CollectedConnection
import logging

logger = logging.getLogger(__name__)

class SeleniumDataCollector:
    """Base class for data collection using Selenium"""
    
    def __init__(self, driver: webdriver.Chrome, user_id: str, platform: str):
        self.driver = driver
        self.user_id = user_id
        self.platform = platform
        self.settings = get_settings()
        
    async def scroll_page(self, scrolls: int = 10, pause_time: int = 2):
        """Scroll page to load more content"""
        for i in range(scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(pause_time)
            
    async def human_delay(self):
        """Add human-like delay"""
        delay = random.uniform(1, 3)
        await asyncio.sleep(delay)


class FacebookDataCollector(SeleniumDataCollector):
    """Facebook-specific data collection"""
    
    async def collect_user_profile(self) -> Dict:
        """Collect user's basic profile information"""
        try:
            # Navigate to user's profile
            profile_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/me/')]")
            if profile_links:
                profile_links[0].click()
                await self.human_delay()
                
            profile_data = {
                "platform": "facebook",
                "user_id": self.user_id,
                "collected_at": datetime.now().isoformat(),
                "name": None,
                "profile_picture": None,
                "cover_photo": None,
                "bio": None,
                "location": None,
                "work": None,
                "education": None,
                "relationship_status": None
            }
            
            try:
                # Extract name
                name_element = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'gmql0nx0')]")
                profile_data["name"] = name_element.text
            except NoSuchElementException:
                pass
                
            try:
                # Extract profile picture
                img_element = self.driver.find_element(By.XPATH, "//image[contains(@class, 'x1ey2m1c')]")
                profile_data["profile_picture"] = img_element.get_attribute("xlink:href")
            except NoSuchElementException:
                pass
                
            return profile_data
            
        except Exception as e:
            logger.error(f"Error collecting Facebook profile: {e}")
            return {}
            
    async def collect_posts(self, max_posts: int = 50) -> List[Dict]:
        """Collect user's posts from Facebook"""
        posts = []
        
        try:
            # Navigate to user's profile posts
            self.driver.get("https://www.facebook.com/me")
            await self.human_delay()
            
            # Scroll to load more posts
            await self.scroll_page(scrolls=5)
            
            # Find post elements
            post_elements = self.driver.find_elements(By.XPATH, "//div[@data-pagelet='FeedUnit_0']//div[contains(@class, 'du4w35lb')]")
            
            for i, post_element in enumerate(post_elements[:max_posts]):
                try:
                    post_data = {
                        "platform": "facebook",
                        "user_id": self.user_id,
                        "post_id": f"fb_post_{i}_{int(datetime.now().timestamp())}",
                        "content": "",
                        "media_urls": [],
                        "likes_count": 0,
                        "comments_count": 0,
                        "shares_count": 0,
                        "timestamp": None,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    # Extract post text
                    try:
                        text_element = post_element.find_element(By.XPATH, ".//div[@data-ad-preview='message']")
                        post_data["content"] = text_element.text
                    except NoSuchElementException:
                        pass
                        
                    # Extract images/videos
                    try:
                        media_elements = post_element.find_elements(By.XPATH, ".//img | .//video")
                        post_data["media_urls"] = [elem.get_attribute("src") for elem in media_elements if elem.get_attribute("src")]
                    except NoSuchElementException:
                        pass
                        
                    # Extract engagement metrics
                    try:
                        likes_element = post_element.find_element(By.XPATH, ".//span[contains(@aria-label, 'reaction')]")
                        likes_text = likes_element.get_attribute("aria-label")
                        likes_match = re.search(r'(\d+)', likes_text)
                        if likes_match:
                            post_data["likes_count"] = int(likes_match.group(1))
                    except NoSuchElementException:
                        pass
                        
                    posts.append(post_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Facebook post {i}: {e}")
                    
            logger.info(f"Collected {len(posts)} Facebook posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error collecting Facebook posts: {e}")
            return posts
            
    async def collect_friends(self) -> List[Dict]:
        """Collect user's friends list"""
        friends = []
        
        try:
            # Navigate to friends page
            self.driver.get("https://www.facebook.com/me/friends")
            await self.human_delay()
            
            # Scroll to load more friends
            await self.scroll_page(scrolls=10)
            
            # Find friend elements
            friend_elements = self.driver.find_elements(By.XPATH, "//div[@data-virtualized='false']//a[contains(@href, '/')]")
            
            for friend_element in friend_elements[:self.settings.SELENIUM_MAX_FRIENDS_TO_COLLECT]:
                try:
                    friend_data = {
                        "platform": "facebook",
                        "user_id": self.user_id,
                        "friend_name": friend_element.get_attribute("aria-label"),
                        "friend_profile_url": friend_element.get_attribute("href"),
                        "mutual_friends": None,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    friends.append(friend_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Facebook friend: {e}")
                    
            logger.info(f"Collected {len(friends)} Facebook friends")
            return friends
            
        except Exception as e:
            logger.error(f"Error collecting Facebook friends: {e}")
            return friends


class InstagramDataCollector(SeleniumDataCollector):
    """Instagram-specific data collection"""
    
    async def collect_posts(self, max_posts: int = 50) -> List[Dict]:
        """Collect user's Instagram posts"""
        posts = []
        
        try:
            # Navigate to user's profile
            self.driver.get("https://www.instagram.com/")
            await self.human_delay()
            
            # Click on profile
            profile_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/') and @tabindex='0']")
            profile_link.click()
            await self.human_delay()
            
            # Scroll to load posts
            await self.scroll_page(scrolls=5)
            
            # Find post links
            post_links = self.driver.find_elements(By.XPATH, "//article//a[contains(@href, '/p/')]")
            
            for i, post_link in enumerate(post_links[:max_posts]):
                try:
                    # Click on post to open
                    post_link.click()
                    await self.human_delay()
                    
                    post_data = {
                        "platform": "instagram",
                        "user_id": self.user_id,
                        "post_id": f"ig_post_{i}_{int(datetime.now().timestamp())}",
                        "content": "",
                        "media_urls": [],
                        "likes_count": 0,
                        "comments_count": 0,
                        "timestamp": None,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    # Extract post caption
                    try:
                        caption_element = self.driver.find_element(By.XPATH, "//article//span[contains(@class, '_aacl _aaco _aacu _aacx _aad7 _aade')]")
                        post_data["content"] = caption_element.text
                    except NoSuchElementException:
                        pass
                        
                    # Extract image/video
                    try:
                        media_element = self.driver.find_element(By.XPATH, "//article//img | //article//video")
                        post_data["media_urls"] = [media_element.get_attribute("src")]
                    except NoSuchElementException:
                        pass
                        
                    # Extract likes count
                    try:
                        likes_element = self.driver.find_element(By.XPATH, "//article//a[contains(@href, '/liked_by/')]")
                        likes_text = likes_element.text
                        likes_match = re.search(r'(\d+)', likes_text.replace(',', ''))
                        if likes_match:
                            post_data["likes_count"] = int(likes_match.group(1))
                    except NoSuchElementException:
                        pass
                        
                    posts.append(post_data)
                    
                    # Close post modal
                    close_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Close')]")
                    close_button.click()
                    await self.human_delay()
                    
                except Exception as e:
                    logger.debug(f"Error parsing Instagram post {i}: {e}")
                    
            logger.info(f"Collected {len(posts)} Instagram posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error collecting Instagram posts: {e}")
            return posts
            
    async def collect_followers(self) -> List[Dict]:
        """Collect user's followers"""
        followers = []
        
        try:
            # Navigate to followers
            followers_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]")
            followers_link.click()
            await self.human_delay()
            
            # Scroll followers list
            await self.scroll_page(scrolls=10)
            
            # Find follower elements
            follower_elements = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/')]")
            
            for follower_element in follower_elements[:self.settings.SELENIUM_MAX_FRIENDS_TO_COLLECT]:
                try:
                    follower_data = {
                        "platform": "instagram",
                        "user_id": self.user_id,
                        "follower_username": follower_element.get_attribute("href").split('/')[-2],
                        "follower_profile_url": follower_element.get_attribute("href"),
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    followers.append(follower_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Instagram follower: {e}")
                    
            logger.info(f"Collected {len(followers)} Instagram followers")
            return followers
            
        except Exception as e:
            logger.error(f"Error collecting Instagram followers: {e}")
            return followers


class RedditDataCollector(SeleniumDataCollector):
    """Reddit-specific data collection"""
    
    async def collect_posts(self, max_posts: int = 50) -> List[Dict]:
        """Collect user's Reddit posts and comments"""
        posts = []
        
        try:
            # Navigate to user profile
            self.driver.get("https://www.reddit.com/user/me/")
            await self.human_delay()
            
            # Scroll to load more content
            await self.scroll_page(scrolls=5)
            
            # Find post elements
            post_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'Post')]")
            
            for i, post_element in enumerate(post_elements[:max_posts]):
                try:
                    post_data = {
                        "platform": "reddit",
                        "user_id": self.user_id,
                        "post_id": f"reddit_post_{i}_{int(datetime.now().timestamp())}",
                        "content": "",
                        "subreddit": "",
                        "upvotes": 0,
                        "comments_count": 0,
                        "timestamp": None,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    # Extract post title/content
                    try:
                        title_element = post_element.find_element(By.XPATH, ".//h3[contains(@class, '_eYtD2XCVieq6emjKBH3m')]")
                        post_data["content"] = title_element.text
                    except NoSuchElementException:
                        pass
                        
                    # Extract subreddit
                    try:
                        subreddit_element = post_element.find_element(By.XPATH, ".//a[contains(@href, '/r/')]")
                        post_data["subreddit"] = subreddit_element.text
                    except NoSuchElementException:
                        pass
                        
                    # Extract upvotes
                    try:
                        upvotes_element = post_element.find_element(By.XPATH, ".//div[contains(@class, '_1rZYMD_4xY3gRcSS3p8ODO')]")
                        upvotes_text = upvotes_element.text
                        upvotes_match = re.search(r'(\d+)', upvotes_text)
                        if upvotes_match:
                            post_data["upvotes"] = int(upvotes_match.group(1))
                    except NoSuchElementException:
                        pass
                        
                    posts.append(post_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Reddit post {i}: {e}")
                    
            logger.info(f"Collected {len(posts)} Reddit posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error collecting Reddit posts: {e}")
            return posts


class YouTubeDataCollector(SeleniumDataCollector):
    """YouTube-specific data collection"""
    
    async def collect_videos(self, max_videos: int = 50) -> List[Dict]:
        """Collect user's YouTube videos"""
        videos = []
        
        try:
            # Navigate to YouTube Studio or channel
            self.driver.get("https://www.youtube.com/channel/UC/videos")
            await self.human_delay()
            
            # Scroll to load more videos
            await self.scroll_page(scrolls=5)
            
            # Find video elements
            video_elements = self.driver.find_elements(By.XPATH, "//div[@id='contents']//a[@id='video-title']")
            
            for i, video_element in enumerate(video_elements[:max_videos]):
                try:
                    video_data = {
                        "platform": "youtube",
                        "user_id": self.user_id,
                        "video_id": f"yt_video_{i}_{int(datetime.now().timestamp())}",
                        "title": video_element.get_attribute("title"),
                        "url": video_element.get_attribute("href"),
                        "views": 0,
                        "likes": 0,
                        "duration": None,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    videos.append(video_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing YouTube video {i}: {e}")
                    
            logger.info(f"Collected {len(videos)} YouTube videos")
            return videos
            
        except Exception as e:
            logger.error(f"Error collecting YouTube videos: {e}")
            return videos
            
    async def collect_subscriptions(self) -> List[Dict]:
        """Collect user's YouTube subscriptions"""
        subscriptions = []
        
        try:
            # Navigate to subscriptions
            self.driver.get("https://www.youtube.com/feed/channels")
            await self.human_delay()
            
            # Scroll to load more
            await self.scroll_page(scrolls=5)
            
            # Find subscription elements
            sub_elements = self.driver.find_elements(By.XPATH, "//a[@class='yt-simple-endpoint style-scope yt-formatted-string']")
            
            for sub_element in sub_elements:
                try:
                    sub_data = {
                        "platform": "youtube",
                        "user_id": self.user_id,
                        "channel_name": sub_element.text,
                        "channel_url": sub_element.get_attribute("href"),
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    subscriptions.append(sub_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing YouTube subscription: {e}")
                    
            logger.info(f"Collected {len(subscriptions)} YouTube subscriptions")
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error collecting YouTube subscriptions: {e}")
            return subscriptions


class TwitterDataCollector(SeleniumDataCollector):
    """Twitter-specific data collection"""
    
    async def collect_tweets(self, max_tweets: int = 50) -> List[Dict]:
        """Collect user's tweets"""
        tweets = []
        
        try:
            # Navigate to user profile
            self.driver.get("https://twitter.com/home")
            await self.human_delay()
            
            # Go to profile
            profile_link = self.driver.find_element(By.XPATH, "//a[@data-testid='AppTabBar_Profile_Link']")
            profile_link.click()
            await self.human_delay()
            
            # Scroll to load tweets
            await self.scroll_page(scrolls=10)
            
            # Find tweet elements
            tweet_elements = self.driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
            
            for i, tweet_element in enumerate(tweet_elements[:max_tweets]):
                try:
                    tweet_data = {
                        "platform": "twitter",
                        "user_id": self.user_id,
                        "tweet_id": f"twitter_tweet_{i}_{int(datetime.now().timestamp())}",
                        "content": "",
                        "retweets": 0,
                        "likes": 0,
                        "replies": 0,
                        "timestamp": None,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    # Extract tweet text
                    try:
                        text_element = tweet_element.find_element(By.XPATH, ".//div[@data-testid='tweetText']")
                        tweet_data["content"] = text_element.text
                    except NoSuchElementException:
                        pass
                        
                    # Extract engagement metrics
                    try:
                        like_element = tweet_element.find_element(By.XPATH, ".//div[@data-testid='like']")
                        like_text = like_element.get_attribute("aria-label")
                        like_match = re.search(r'(\d+)', like_text)
                        if like_match:
                            tweet_data["likes"] = int(like_match.group(1))
                    except NoSuchElementException:
                        pass
                        
                    tweets.append(tweet_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Twitter tweet {i}: {e}")
                    
            logger.info(f"Collected {len(tweets)} Twitter tweets")
            return tweets
            
        except Exception as e:
            logger.error(f"Error collecting Twitter tweets: {e}")
            return tweets
            
    async def collect_following(self) -> List[Dict]:
        """Collect user's Twitter following"""
        following = []
        
        try:
            # Navigate to following page
            following_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/following')]")
            following_link.click()
            await self.human_delay()
            
            # Scroll to load more
            await self.scroll_page(scrolls=10)
            
            # Find following elements
            following_elements = self.driver.find_elements(By.XPATH, "//div[@data-testid='UserCell']")
            
            for following_element in following_elements[:self.settings.SELENIUM_MAX_FRIENDS_TO_COLLECT]:
                try:
                    username_element = following_element.find_element(By.XPATH, ".//span[contains(text(), '@')]")
                    username = username_element.text
                    
                    following_data = {
                        "platform": "twitter",
                        "user_id": self.user_id,
                        "following_username": username,
                        "collected_at": datetime.now().isoformat()
                    }
                    
                    following.append(following_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Twitter following: {e}")
                    
            logger.info(f"Collected {len(following)} Twitter following")
            return following
            
        except Exception as e:
            logger.error(f"Error collecting Twitter following: {e}")
            return following


class DataCollectorFactory:
    """Factory to create platform-specific collectors"""
    
    @staticmethod
    def create_collector(platform: str, driver: webdriver.Chrome, user_id: str):
        """Create appropriate collector for platform"""
        collectors = {
            "facebook": FacebookDataCollector,
            "instagram": InstagramDataCollector,
            "reddit": RedditDataCollector,
            "youtube": YouTubeDataCollector,
            "twitter": TwitterDataCollector
        }
        
        collector_class = collectors.get(platform.lower())
        if not collector_class:
            raise ValueError(f"Unsupported platform: {platform}")
            
        return collector_class(driver, user_id, platform)