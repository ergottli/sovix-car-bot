#!/usr/bin/env python3
"""
Test script to verify the bot setup
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database.db import db
from utils.rag_client import rag_client

async def test_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    try:
        await db.connect()
        print("✅ Database connection successful")
        
        # Test creating a user
        test_user_id = 123456789
        success = await db.bootstrap_admin(test_user_id, "test_admin", "test_secret")
        if success:
            print("✅ Database operations working")
        else:
            print("⚠️ Database operations failed (expected if user already exists)")
        
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_environment_variables():
    """Test environment variables"""
    print("🔍 Testing environment variables...")
    
    required_vars = [
        'BOT_TOKEN',
        'ADMIN_BOOTSTRAP_SECRET', 
        'RAG_API_URL',
        'RAG_API_KEY',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_rag_client():
    """Test RAG client initialization"""
    print("🔍 Testing RAG client...")
    try:
        # Just test if we can create the client
        client = rag_client
        print("✅ RAG client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ RAG client initialization failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚗 Car Assistant Bot - Setup Test\n")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("RAG Client", test_rag_client),
        ("Database Connection", test_database_connection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot is ready to run.")
        print("\nTo start the bot:")
        print("  docker compose up -d")
        print("  # or")
        print("  python bot.py")
    else:
        print("⚠️ Some tests failed. Please check the configuration.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
