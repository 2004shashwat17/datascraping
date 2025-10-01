#!/usr/bin/env python3
"""
Test script for TwitterApiIOCollector
Demonstrates how to use twitterapi.io for Twitter data collection
"""

import asyncio
import os
from app.services.twitter_api_io_collector import TwitterApiIOCollector

async def test_twitter_collection():
    """Test Twitter data collection using TwitterApiIO"""

    # Get API key from environment
    api_key = os.getenv("TWITTER_API_IO_KEY")
    if not api_key:
        print("❌ TWITTER_API_IO_KEY environment variable not set")
        print("Please set your TwitterApiIO API key:")
        print("export TWITTER_API_IO_KEY='your_api_key_here'")
        return

    print("🔍 Testing TwitterApiIO Collector...")
    print(f"API Key configured: {'Yes' if api_key else 'No'}")

    try:
        async with TwitterApiIOCollector(api_key) as collector:
            # Test getting user profile
            print("\n📋 Testing user profile collection...")
            username = "elonmusk"  # Test with a public account
            profile = await collector.get_user_profile(username)

            if profile:
                print(f"✅ Profile collected for @{profile['username']}")
                print(f"   Name: {profile['name']}")
                print(f"   Followers: {profile['followers_count']}")
                print(f"   Bio: {profile['bio'][:100]}...")
            else:
                print(f"❌ Failed to get profile for @{username}")

            # Test getting user tweets
            print(f"\n📝 Testing tweet collection for @{username}...")
            tweets = await collector.get_user_tweets(username, count=3)

            if tweets:
                print(f"✅ Collected {len(tweets)} tweets:")
                for i, tweet in enumerate(tweets[:3], 1):
                    print(f"   {i}. {tweet['text'][:100]}...")
            else:
                print(f"❌ Failed to get tweets for @{username}")

            # Test search functionality
            print("\n🔎 Testing tweet search...")
            search_query = "python programming"
            search_results = await collector.search_tweets(search_query, count=2)

            if search_results:
                print(f"✅ Found {len(search_results)} tweets for '{search_query}':")
                for i, tweet in enumerate(search_results[:2], 1):
                    print(f"   {i}. @{tweet['username']}: {tweet['text'][:80]}...")
            else:
                print(f"❌ No tweets found for '{search_query}'")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🐦 TwitterApiIO Collector Test")
    print("=" * 40)
    asyncio.run(test_twitter_collection())