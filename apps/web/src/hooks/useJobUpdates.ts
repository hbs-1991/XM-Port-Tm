/**
 * useJobUpdates hook for WebSocket job updates
 */
'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from './useAuth'

export interface JobUpdateMessage {
  type: 'job_update';
  data: {
    jobId: string;
    status: 'completed' | 'processing' | 'failed' | 'pending';
    progress?: number;
    completedAt?: string;
    errorMessage?: string;
    productsCount?: number;
    confidenceScore?: number;
  };
}

export interface ConnectionStatus {
  connected: boolean;
  reconnecting: boolean;
  error: string | null;
}

interface UseJobUpdatesReturn {
  connectionStatus: ConnectionStatus;
  lastUpdate: JobUpdateMessage['data'] | null;
  updatedJobIds: Set<string>;
  connect: () => void;
  disconnect: () => void;
  clearUpdatedJobs: () => void;
}

export const useJobUpdates = (): UseJobUpdatesReturn => {
  const { session } = useAuth()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false,
    reconnecting: false,
    error: null
  })
  const [lastUpdate, setLastUpdate] = useState<JobUpdateMessage['data'] | null>(null)
  const [updatedJobIds, setUpdatedJobIds] = useState<Set<string>>(new Set())
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5
  
  const clearUpdatedJobs = useCallback(() => {
    setUpdatedJobIds(new Set())
  }, [])

  const connect = useCallback(() => {
    if (!session?.accessToken) {
      console.warn('Cannot connect to WebSocket: No access token')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    try {
      // Use wss for production, ws for development
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/api/ws/jobs?token=${session.accessToken}`
      
      console.log('Connecting to WebSocket:', wsUrl)
      setConnectionStatus(prev => ({ ...prev, reconnecting: true, error: null }))
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected successfully')
        setConnectionStatus({
          connected: true,
          reconnecting: false,
          error: null
        })
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: JobUpdateMessage = JSON.parse(event.data)
          
          if (message.type === 'job_update') {
            console.log('Received job update:', message.data)
            setLastUpdate(message.data)
            
            // Track updated job IDs for UI highlighting
            setUpdatedJobIds(prev => new Set([...prev, message.data.jobId]))
            
            // Clear the update highlight after 5 seconds
            setTimeout(() => {
              setUpdatedJobIds(prev => {
                const newSet = new Set(prev)
                newSet.delete(message.data.jobId)
                return newSet
              })
            }, 5000)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus(prev => ({
          ...prev,
          error: 'Connection error occurred'
        }))
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setConnectionStatus(prev => ({
          ...prev,
          connected: false,
          reconnecting: false
        }))
        wsRef.current = null

        // Attempt to reconnect if not closed intentionally
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connect()
          }, delay)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setConnectionStatus(prev => ({
            ...prev,
            error: 'Max reconnection attempts reached'
          }))
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
      setConnectionStatus(prev => ({
        ...prev,
        reconnecting: false,
        error: 'Failed to create connection'
      }))
    }
  }, [session?.accessToken])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    if (wsRef.current) {
      console.log('Disconnecting WebSocket')
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    
    setConnectionStatus({
      connected: false,
      reconnecting: false,
      error: null
    })
    reconnectAttemptsRef.current = 0
  }, [])

  // Auto-connect when session is available
  useEffect(() => {
    if (session?.accessToken) {
      connect()
    }
    
    return () => {
      disconnect()
    }
  }, [session?.accessToken, connect, disconnect])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      disconnect()
    }
  }, [disconnect])

  return {
    connectionStatus,
    lastUpdate,
    updatedJobIds,
    connect,
    disconnect,
    clearUpdatedJobs
  }
}