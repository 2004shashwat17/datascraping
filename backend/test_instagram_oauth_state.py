`#!/usr/bin/env python3
"""
Test script for Instagram OAuth state verification with its own endpoints
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.mongodb import init_database
from app.models.social_auth_models import OAuthState, PlatformType
from app.services.oauth_service import OAuthService

async def test_instagram_oauth_flow():
    """Test Instagram OAuth state storage and verification"""

    print("🔍 Testing Instagram OAuth state management...")

    # Initialize database
    await init_database()

    # Create OAuth service
    oauth_service = OAuthService()

    # Test getting authorization URL for Instagram
    print("📝 Testing Instagram authorization URL generation...")
    try:
        auth_url, state = await oauth_service.get_authorization_url("instagram", "test_user_123")
        print(f"✅ Authorization URL generated: {auth_url[:100]}...")
        print(f"   State: {state}")
    except Exception as e:
        print(f"❌ Failed to generate authorization URL: {e}")
        return False

    # Verify the state was stored correctly
    print("🔄 Verifying state storage...")
    stored_data = await oauth_service._verify_oauth_state(state, "instagram")
    
    if stored_data:
        print("✅ State verification successful!")
        print(f"   User ID: {stored_data['user_id']}")
        print(f"   Platform: {stored_data['platform']}")
    else:
        print("❌ State verification failed!")
        return False

    # Try to verify the same state again (should fail as it's marked as used)
    print("🔄 Testing state reuse prevention...")
    stored_data_again = await oauth_service._verify_oauth_state(state, "instagram")
    
    if not stored_data_again:
        print("✅ State reuse prevention working!")
    else:
        print("❌ State reuse prevention failed!")
        return False

    return True

async def main():
    try:
        success = await test_instagram_oauth_flow()
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())