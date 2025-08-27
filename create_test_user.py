#!/usr/bin/env python3
"""Create a test user and get token."""

import requests
import json
import sys

def register_user():
    """Register a new test user."""
    
    url = "http://localhost:8000/api/v1/auth/register"
    
    user_data = {
        "email": "wstest@example.com",
        "password": "TestPassword123!",
        "first_name": "WebSocket",
        "last_name": "Tester",
        "company_name": "WebSocket Test Company"
    }
    
    response = requests.post(url, json=user_data)
    
    if response.status_code == 201:
        print("✅ User registered successfully!")
        return True
    elif response.status_code == 400:
        # User might already exist
        print("ℹ️  User might already exist, trying login...")
        return True
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.text)
        return False

def login_user():
    """Login and get token."""
    
    url = "http://localhost:8000/api/v1/auth/login"
    
    credentials = {
        "email": "wstest@example.com",
        "password": "TestPassword123!"
    }
    
    response = requests.post(url, json=credentials)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Login successful!")
        # The response has tokens nested
        if 'tokens' in data and 'access_token' in data['tokens']:
            return data['tokens']['access_token']
        elif 'access_token' in data:
            return data['access_token']
        else:
            print(f"Response data: {json.dumps(data, indent=2)}")
            return None
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    # Try to register user
    register_user()
    
    # Login and get token
    token = login_user()
    
    if token:
        print(f"\n📋 Access Token:\n{token}\n")
        print("Test WebSocket with:")
        print(f"python3 test_ws_connection.py '{token}'")