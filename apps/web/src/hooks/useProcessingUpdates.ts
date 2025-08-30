'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { 
  webSocketService, 
  type ProcessingUpdateMessage, 
  type NotificationMessage, 
  type WebSocketMessage,
  type ConnectionStatus 
} from '../services/websocketService'

interface UseProcessingUpdatesOptions {
  autoReconnect?: boolean
  reconnectDelay?: number
  maxReconnectAttempts?: number
}

interface UseProcessingUpdatesReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  notifications: NotificationMessage[]
  sendMessage: (message: any) => void
  clearNotifications: () => void
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
}

export const useProcessingUpdates = (
  options: UseProcessingUpdatesOptions = {}
): UseProcessingUpdatesReturn => {
  const { data: session } = useSession()
  const token = session?.accessToken
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [notifications, setNotifications] = useState<NotificationMessage[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const addNotification = useCallback((notification: NotificationMessage) => {
    setNotifications(prev => [notification, ...prev.slice(0, 9)]) // Keep last 10 notifications
  }, [])

  const sendMessage = useCallback((message: any) => {
    webSocketService.sendMessage('processing', message)
  }, [])

  // Set up WebSocket service subscription
  useEffect(() => {
    if (!token) {
      setConnectionStatus('disconnected')
      setIsConnected(false)
      return
    }

    // Update token in service
    webSocketService.setToken(token)

    // Subscribe to processing updates
    const unsubscribe = webSocketService.subscribe('processing')

    // Listen for status updates
    const handleStatusUpdate = (status: ConnectionStatus) => {
      setIsConnected(status.connected)
      
      // Map ConnectionStatus to component's connectionStatus type
      if (status.reconnecting) {
        setConnectionStatus('connecting')
      } else if (status.connected) {
        setConnectionStatus('connected')
      } else if (status.error) {
        setConnectionStatus('error')
      } else {
        setConnectionStatus('disconnected')
      }
    }

    // Listen for processing update messages
    const handleMessage = (message: WebSocketMessage) => {
      setLastMessage(message)

      // Handle different message types
      if (message.type === 'processing_update') {
        // Create a notification for processing updates
        const updateNotification: NotificationMessage = {
          type: 'notification',
          level: message.status === 'COMPLETED' ? 'success' : 
                 message.status === 'FAILED' ? 'error' : 'info',
          message: message.message || `Job ${message.job_id} status: ${message.status}`,
          timestamp: message.timestamp
        }
        addNotification(updateNotification)
      } else if (message.type === 'notification') {
        addNotification(message)
      }
    }

    webSocketService.on('processing:status', handleStatusUpdate)
    webSocketService.on('processing:message', handleMessage)

    // Set initial status
    const initialStatus = webSocketService.getConnectionStatus('processing')
    handleStatusUpdate(initialStatus)

    return () => {
      webSocketService.off('processing:status', handleStatusUpdate)
      webSocketService.off('processing:message', handleMessage)
      unsubscribe()
    }
  }, [token, addNotification])

  return {
    isConnected,
    lastMessage,
    notifications,
    sendMessage,
    clearNotifications,
    connectionStatus
  }
}