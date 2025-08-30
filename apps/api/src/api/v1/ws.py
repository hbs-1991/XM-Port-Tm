"""
WebSocket API endpoints for real-time processing updates
"""
import asyncio
import json
import logging
import time
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.auth import get_current_user_ws
from src.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

# Global connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections for a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.active_connections[user_id].discard(connection)

    async def send_job_update(self, job_id: str, user_id: str, status: str, progress: int = 0, message: str = "", data: dict = None):
        """Send job update to user"""
        update_message = {
            "type": "job_update",
            "data": {
                "jobId": job_id,
                "status": status,
                "progress": progress,
                "errorMessage": message if status == "failed" else None,
                "completedAt": data.get("completedAt") if data else None,
                "productsCount": data.get("productsCount") if data else None,
                "confidenceScore": data.get("confidenceScore") if data else None,
            }
        }
        await self.send_personal_message(update_message, user_id)

manager = ConnectionManager()


@router.websocket("/jobs")
async def websocket_job_updates(
    websocket: WebSocket,
    token: str = None,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time job updates"""
    logger.info(f"WebSocket jobs connection attempt - Token present: {bool(token)}")
    
    try:
        # Authenticate user via token
        user = None
        if token:
            try:
                user = await get_current_user_ws(token)
                user_id = str(user.id)
                logger.info(f"WebSocket jobs authenticated for user {user_id}")
            except Exception as e:
                logger.error(f"WebSocket jobs authentication failed: {e}")
                await websocket.close(code=4001, reason="Authentication failed")
                return
        else:
            logger.warning("WebSocket jobs connection attempt without token")
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        await manager.connect(websocket, user_id)
        
        try:
            # Send initial connection confirmation
            await websocket.send_text(json.dumps({"type": "connected", "message": "WebSocket jobs connected successfully"}))
            
            while True:
                try:
                    # Keep connection alive and handle any client messages with timeout
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    logger.info(f"Received message from jobs WebSocket: {data}")
                    
                    # Parse and handle the message
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            await websocket.send_text(json.dumps({"type": "pong", "message": "Connection alive"}))
                        else:
                            # Handle other message types as needed
                            await websocket.send_text(json.dumps({"type": "ack", "message": "Message received"}))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received: {data}")
                        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON format"}))
                    except Exception as send_error:
                        logger.error(f"Error sending WebSocket response: {send_error}")
                        break
                        
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive every 30 seconds
                    try:
                        await websocket.send_text(json.dumps({"type": "ping", "message": "Keep alive"}))
                    except Exception as ping_error:
                        logger.error(f"Error sending ping: {ping_error}")
                        break
                    continue
                except Exception as e:
                    logger.error(f"Error in jobs WebSocket loop: {e}")
                    break
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket jobs disconnected for user {user_id}")
            manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket jobs error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


@router.websocket("/processing-updates")
async def websocket_processing_updates(
    websocket: WebSocket,
    token: str = None,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time processing updates"""
    logger.info(f"WebSocket processing-updates connection attempt - Token present: {bool(token)}")
    
    try:
        # Authenticate user via token
        user = None
        if token:
            try:
                user = await get_current_user_ws(token)
                user_id = str(user.id)
                logger.info(f"WebSocket processing-updates authenticated for user {user_id}")
            except Exception as e:
                logger.error(f"WebSocket processing-updates authentication failed: {e}")
                await websocket.close(code=4001, reason="Authentication failed")
                return
        else:
            logger.warning("WebSocket processing-updates connection attempt without token")
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        await manager.connect(websocket, user_id)
        
        try:
            # Send initial connection confirmation
            await websocket.send_text(json.dumps({"type": "connected", "message": "WebSocket processing-updates connected successfully"}))
            
            while True:
                try:
                    # Keep connection alive and handle any client messages with timeout
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    logger.info(f"Received message from processing-updates WebSocket: {data}")
                    
                    # Parse and handle the message
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            await websocket.send_text(json.dumps({"type": "pong", "message": "Connection alive"}))
                        else:
                            # Handle other message types as needed
                            await websocket.send_text(json.dumps({"type": "ack", "message": "Message received"}))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received: {data}")
                        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON format"}))
                    except Exception as send_error:
                        logger.error(f"Error sending WebSocket response: {send_error}")
                        break
                        
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive every 30 seconds
                    try:
                        await websocket.send_text(json.dumps({"type": "ping", "message": "Keep alive"}))
                    except Exception as ping_error:
                        logger.error(f"Error sending ping: {ping_error}")
                        break
                    continue
                except Exception as e:
                    logger.error(f"Error in processing-updates WebSocket loop: {e}")
                    break
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket processing-updates disconnected for user {user_id}")
            manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket processing-updates error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass