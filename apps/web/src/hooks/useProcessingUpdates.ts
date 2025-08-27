'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'

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

  const { data: session } = useSession()
  const token = session?.accessToken
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
      setConnectionStatus('disconnected')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    // Don't try to connect if already connecting
    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    try {
      setConnectionStatus('connecting')
      const wsUrl = process.env.NODE_ENV === 'production' 
        ? `wss://${window.location.host}/api/v1/ws/processing-updates?token=${encodeURIComponent(token)}`
        : `ws://localhost:8000/api/v1/ws/processing-updates?token=${encodeURIComponent(token)}`

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
        console.log('WebSocket disconnected:', {
          code: event.code,
          reason: event.reason || 'No reason provided',
          wasClean: event.wasClean,
          timestamp: new Date().toISOString(),
          isManualClose: isManualClose.current,
          reconnectAttempts: reconnectAttemptsRef.current
        })
        setIsConnected(false)
        wsRef.current = null

        if (!isManualClose.current && autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          setConnectionStatus('connecting')
          reconnectAttemptsRef.current += 1
          
          // Add reconnection notification
          const reconnectNotification: WebSocketNotification = {
            type: 'notification',
            level: 'warning',
            message: `Connection lost. Reconnecting... (Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`,
            timestamp: Date.now()
          }
          addNotification(reconnectNotification)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectDelay * Math.pow(1.5, reconnectAttemptsRef.current - 1)) // Exponential backoff
        } else {
          setConnectionStatus(isManualClose.current ? 'disconnected' : 'error')
          
          if (!isManualClose.current && reconnectAttemptsRef.current >= maxReconnectAttempts) {
            // Max reconnect attempts reached
            const maxAttemptsNotification: WebSocketNotification = {
              type: 'notification',
              level: 'error',
              message: 'Connection could not be restored. Please refresh the page to try again.',
              timestamp: Date.now()
            }
            addNotification(maxAttemptsNotification)
          }
        }
      }

      ws.onerror = (error) => {
        const errorDetails = {
          timestamp: new Date().toISOString(),
          readyState: ws.readyState,
          url: ws.url,
          errorType: error?.type || 'unknown',
          target: error?.target?.constructor?.name || 'WebSocket',
          reconnectAttempts: reconnectAttemptsRef.current
        }
        console.error('WebSocket error occurred:')
        console.error(errorDetails)
        setConnectionStatus('error')
        
        // Add user-friendly notification
        const errorNotification: WebSocketNotification = {
          type: 'notification',
          level: 'error',
          message: 'Connection error occurred. Attempting to reconnect...',
          timestamp: Date.now()
        }
        addNotification(errorNotification)
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
        timestamp: new Date().toISOString(),
        token: token ? '***present***' : 'missing',
        reconnectAttempts: reconnectAttemptsRef.current
      })
      setConnectionStatus('error')
      
      // Add user-friendly notification
      const connectionErrorNotification: WebSocketNotification = {
        type: 'notification',
        level: 'error',
        message: 'Failed to establish connection. Please check your network and try again.',
        timestamp: Date.now()
      }
      addNotification(connectionErrorNotification)
    }
  }, [token, autoReconnect, reconnectDelay, maxReconnectAttempts, addNotification])

  const disconnect = useCallback(() => {
    isManualClose.current = true
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      const ws = wsRef.current
      const state = ws.readyState
      
      if (state === WebSocket.OPEN) {
        ws.close(1000, 'Manual disconnect')
      } else if (state === WebSocket.CONNECTING) {
        // If still connecting, wait for connection then close
        ws.addEventListener('open', () => {
          ws.close(1000, 'Manual disconnect')
        })
        // Also add error handler to clean up if connection fails
        ws.addEventListener('error', () => {
          wsRef.current = null
        })
      }
      // If CLOSING or CLOSED, nothing to do
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