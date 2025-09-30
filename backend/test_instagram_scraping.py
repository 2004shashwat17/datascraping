#!/usr/bin/env python3
"""
Instagram Data Collector Test Script
Allows testing Instagram scraping with terminal output
"""

import asyncio
import logging
from typing import List, Dict
from getpass import getpass

from app.services.instagram_instaloader_collector import InstagramInstaloaderCollector
from app.core.mongodb import connect_to_mongo

# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

def print_separator(title: str = ""):
    """Print a nice separator line"""
    if title:
        print(f"\n{'='*20} {title} {'='*20}")
    else:
        print("="*50)

def print_warning():
    """Print Instagram scraping warnings"""
    print("\n⚠️  IMPORTANT NOTES:")
    print("• Instagram frequently changes their API and login process")
    print("• Automated scraping may be blocked or rate-limited")
    print("• Use this for educational/testing purposes only")
    print("• Respect Instagram's Terms of Service")
    print("• Consider using official Instagram APIs for production use")

def print_post_data(posts: List[Dict]):
    """Pretty print post data to terminal"""
    if not posts:
        print("❌ No posts found!")
        return

    print(f"✅ Found {len(posts)} posts!")
    print_separator("POST DETAILS")

    for i, post in enumerate(posts, 1):
        print(f"\n📱 Post #{i}")
        print(f"   ID: {post.get('post_id', 'N/A')}")
        print(f"   Author: {post.get('author_username', 'N/A')}")
        print(f"   Content: {post.get('content', 'N/A')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}")
        print(f"   Likes: {post.get('likes_count', 0)}")
        print(f"   Comments: {post.get('comments_count', 0)}")
        print(f"   Posted: {post.get('posted_at', 'N/A')}")
        print(f"   URL: {post.get('url', 'N/A')}")

        # Show hashtags and mentions
        hashtags = post.get('hashtags', [])
        mentions = post.get('mentions', [])
        if hashtags:
            print(f"   Hashtags: {', '.join(hashtags)}")
        if mentions:
            print(f"   Mentions: {', '.join(mentions)}")

        # Show media URLs (first one only for brevity)
        media_urls = post.get('media_urls', [])
        if media_urls:
            print(f"   Media: {len(media_urls)} file(s) - {media_urls[0][:50]}...")

async def test_instagram_scraping():
    """Main test function for Instagram scraping"""
    print_separator("INSTAGRAM SCRAPING TEST")
    print("🔍 This script will test Instagram data collection")
    print("📝 You'll need valid Instagram credentials to proceed")

    print_warning()

    # Get user input
    username = input("\n👤 Enter Instagram username: ").strip()
    if not username:
        print("❌ Username is required!")
        return

    password = getpass("🔒 Enter Instagram password: ").strip()
    if not password:
        print("❌ Password is required!")
        return

    # Choose target type
    print("\n🎯 Choose what to scrape:")
    print("1. Profile posts (e.g., @instagram)")
    print("2. Hashtag posts (e.g., #python)")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        target_type = "profile"
        target = input("Enter profile username (without @): ").strip()
        if not target:
            print("❌ Profile username is required!")
            return
    elif choice == "2":
        target_type = "hashtag"
        target = input("Enter hashtag (without #): ").strip()
        if not target:
            print("❌ Hashtag is required!")
            return
    else:
        print("❌ Invalid choice!")
        return

    # Get number of posts
    try:
        max_posts = int(input("Enter number of posts to collect (1-20): ").strip())
        if max_posts < 1 or max_posts > 20:
            print("❌ Please enter a number between 1 and 20!")
            return
    except ValueError:
        print("❌ Invalid number!")
        return

    print_separator("STARTING SCRAPING PROCESS")

    # Initialize collector
    print("🔧 Initializing Instagram collector...")
    collector = InstagramInstaloaderCollector(username, password)

    # Test login
    print("🔐 Attempting login...")
    print("⏳ This may take a moment due to Instagram's anti-bot measures...")

    login_success = collector.login()
    if not login_success:
        print("\n❌ Login failed!")
        print("💡 Possible solutions:")
        print("   • Check your username and password")
        print("   • Try again in a few minutes (Instagram may be rate limiting)")
        print("   • Disable 2FA temporarily if enabled")
        print("   • Use a different Instagram account")
        print("   • Instagram may have updated their login process")
        return

    print("✅ Login successful!")

    # Collect data
    print(f"📊 Collecting {max_posts} posts from {target_type}: {target}")
    print("⏳ This may take 30-90 seconds depending on network and Instagram limits...")
    print("💡 If this takes too long, Instagram might be rate limiting requests")

    try:
        if target_type == "profile":
            posts_data = collector.collect_posts_from_profile(target, max_posts)
        else:  # hashtag
            posts_data = collector.collect_hashtag_posts(target, max_posts)

        # Display results
        print_post_data(posts_data)

        # Option to save to database
        if posts_data:
            save_choice = input(f"\n💾 Save {len(posts_data)} posts to database? (y/n): ").strip().lower()
            if save_choice == 'y':
                print("💾 Saving to database...")
                saved_count = await collector.save_posts_to_db(posts_data)
                print(f"✅ Saved {saved_count} posts to database!")

        print_separator("TEST COMPLETED")
        print("🎉 Instagram scraping test finished!")

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        print("💡 This could be due to:")
        print("   • Instagram rate limiting")
        print("   • Network connectivity issues")
        print("   • Instagram API changes")
        logger.error(f"Scraping error: {e}")

async def main():
    """Main entry point"""
    # Connect to database first
    print("🔌 Connecting to database...")
    db_connected = await connect_to_mongo()
    if db_connected:
        print("✅ Database connected!")
    else:
        print("⚠️  Database connection failed, but continuing with test...")

    # Run the test
    await test_instagram_scraping()

if __name__ == "__main__":
    asyncio.run(main())