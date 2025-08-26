'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from './useAuth'

export interface ProcessingUpdate {
  type: 'processing_update'
  job_id: string
  status: string
  progress: number
  message: string
  timestamp: number
  data?: Record<string, any>
}

export interface WebSocketNotification {
  type: 'notification'
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  timestamp: number
}

export type WebSocketMessage = ProcessingUpdate | WebSocketNotification

interface UseProcessingUpdatesOptions {
  autoReconnect?: boolean
  reconnectDelay?: number
  maxReconnectAttempts?: number
}

interface UseProcessingUpdatesReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  notifications: WebSocketNotification[]
  sendMessage: (message: any) => void
  clearNotifications: () => void
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
}

export const useProcessingUpdates = (
  options: UseProcessingUpdatesOptions = {}
): UseProcessingUpdatesReturn => {
  const {
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5
  } = options

  const { token } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [notifications, setNotifications] = useState<WebSocketNotification[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isManualClose = useRef(false)

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const addNotification = useCallback((notification: WebSocketNotification) => {
    setNotifications(prev => [notification, ...prev.slice(0, 9)]) // Keep last 10 notifications
  }, [])

  const connect = useCallback(() => {
    if (!token) {
      setConnectionStatus('error')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    try {
      setConnectionStatus('connecting')
      const wsUrl = process.env.NODE_ENV === 'production' 
        ? `wss://${window.location.host}/ws/processing-updates?token=${encodeURIComponent(token)}`
        : `ws://localhost:8000/ws/processing-updates?token=${encodeURIComponent(token)}`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionStatus('connected')
        reconnectAttemptsRef.current = 0
        
        // Send ping to keep connection alive
        ws.send(JSON.stringify({ type: 'ping' }))
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)

          // Handle different message types
          if (message.type === 'processing_update') {
            // Create a notification for processing updates
            const updateNotification: WebSocketNotification = {
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
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        setIsConnected(false)
        wsRef.current = null

        if (!isManualClose.current && autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          setConnectionStatus('connecting')
          reconnectAttemptsRef.current += 1
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectDelay * Math.pow(1.5, reconnectAttemptsRef.current - 1)) // Exponential backoff
        } else {
          setConnectionStatus(isManualClose.current ? 'disconnected' : 'error')
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('error')
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionStatus('error')
    }
  }, [token, autoReconnect, reconnectDelay, maxReconnectAttempts, addNotification])

  const disconnect = useCallback(() => {
    isManualClose.current = true
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
    setConnectionStatus('disconnected')
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  // Connect when token becomes available
  useEffect(() => {
    if (token) {
      isManualClose.current = false
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [token, connect, disconnect])

  // Send periodic ping to keep connection alive
  useEffect(() => {
    if (!isConnected) return

    const interval = setInterval(() => {
      sendMessage({ type: 'ping' })
    }, 30000) // Ping every 30 seconds

    return () => clearInterval(interval)
  }, [isConnected, sendMessage])

  return {
    isConnected,
    lastMessage,
    notifications,
    sendMessage,
    clearNotifications,
    connectionStatus
  }
}