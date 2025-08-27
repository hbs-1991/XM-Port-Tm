#!/usr/bin/env python3
"""Get a valid test token from the API."""

import requests
import json
import sys

def get_token():
    """Login and get a valid access token."""
    
    # Test credentials
    email = "test@test.com"
    password = "testPassword123!"
    
    # Login endpoint
    url = "http://localhost:8000/api/v1/auth/login"
    
    # Login request
    response = requests.post(
        url,
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Token obtained successfully!")
        print(f"\nAccess Token:\n{data['access_token']}\n")
        print(f"User ID: {data['user']['id']}")
        print(f"Email: {data['user']['email']}")
        return data['access_token']
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    token = get_token()
    if token:
        print(f"\nTest WebSocket with:\npython3 test_ws_connection.py '{token}'")