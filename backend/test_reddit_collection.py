import asyncio
from app.core.mongodb import connect_to_mongo
from app.services.oauth_data_collector import OAuthDataCollector

async def test_reddit_collection():
    await connect_to_mongo()

    collector = OAuthDataCollector()

    # Test collection for the user ID we found
    user_id = '68db673c0184b711d7852cc3'

    print(f'Testing Reddit data collection for user: {user_id}')

    try:
        result = await collector.collect_data_for_user(user_id)
        print('Collection result:')
        print(f'- Posts collected: {result.get("posts_saved", 0)}')
        print(f'- Connections collected: {result.get("connections_saved", 0)}')
        print(f'- Interactions collected: {result.get("interactions_saved", 0)}')
        print(f'- Platform results: {result.get("platform_results", {})}')

        if 'warnings' in result:
            print('Warnings:')
            for warning in result['warnings']:
                print(f'- {warning}')

    except Exception as e:
        print(f'Error during collection: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reddit_collection())