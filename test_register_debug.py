#!/usr/bin/env python3
"""
Debug script to test user registration issue
"""
import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, 'apps/api/src')

from src.services.auth_service import AuthService
from src.services.session_service import SessionService
from src.repositories.user_repository import UserRepository
from src.models.user import User, UserRole
from src.core.config import settings

async def test_registration():
    print("Testing user registration step by step...")
    
    # Initialize services
    auth_service = AuthService()
    session_service = SessionService()
    user_repository = UserRepository()
    
    email = "debug@test.com"
    
    try:
        print(f"1. Checking if user {email} already exists...")
        existing_user = await user_repository.get_by_email(email)
        print(f"   Existing user: {existing_user}")
        
        if existing_user:
            print("   User already exists, skipping creation")
            return
            
        print("2. Creating new user...")
        hashed_password = auth_service.hash_password("password123")
        
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            first_name="Debug",
            last_name="User",
            company_name="Test Co",
            country="USA",
            role=UserRole.USER
        )
        
        print("3. Saving user to database...")
        created_user = await user_repository.create(new_user)
        print(f"   Created user: {created_user.id} - {created_user.email}")
        
        print("4. Generating tokens...")
        access_token, refresh_token = auth_service.generate_token_pair(created_user)
        print(f"   Access token length: {len(access_token)}")
        print(f"   Refresh token length: {len(refresh_token)}")
        
        print("5. Storing refresh token in Redis...")
        await session_service.store_refresh_token(str(created_user.id), refresh_token)
        print("   Refresh token stored successfully")
        
        print("6. Verifying user was actually created...")
        verify_user = await user_repository.get_by_email(email)
        if verify_user:
            print(f"   ✅ User verified in database: {verify_user.id}")
        else:
            print("   ❌ User NOT found in database after creation!")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session_service.close()

if __name__ == "__main__":
    asyncio.run(test_registration())