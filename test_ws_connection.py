#!/usr/bin/env python3
"""Test WebSocket connection to the backend."""

import asyncio
import json
import websockets
import sys

async def test_websocket():
    # Replace with an actual valid token
    token = sys.argv[1] if len(sys.argv) > 1 else "test_token"
    
    uri = f"ws://localhost:8000/api/v1/ws/processing-updates?token={token}"
    
    print(f"Attempting to connect to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Send a ping message
            await websocket.send(json.dumps({"type": "ping"}))
            print("📤 Sent ping message")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"📥 Received: {response}")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection rejected with status {e.status_code}: {e.headers}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: code={e.code}, reason={e.reason}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())