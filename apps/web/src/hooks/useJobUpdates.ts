/**
 * useJobUpdates hook for WebSocket job updates
 * Now uses the unified WebSocket service for better connection management
 */
'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from './useAuth'
import { webSocketService, type JobUpdateMessage, type ConnectionStatus } from '../services/websocketService'

interface UseJobUpdatesReturn {
  connectionStatus: ConnectionStatus
  lastUpdate: JobUpdateMessage['data'] | null
  updatedJobIds: Set<string>
  connect: () => void
  disconnect: () => void
  clearUpdatedJobs: () => void
}

export const useJobUpdates = (): UseJobUpdatesReturn => {
  const { session } = useAuth()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false,
    reconnecting: false,
    error: null,
    connectionCount: 0
  })
  const [lastUpdate, setLastUpdate] = useState<JobUpdateMessage['data'] | null>(null)
  const [updatedJobIds, setUpdatedJobIds] = useState<Set<string>>(new Set())
  
  const clearUpdatedJobs = useCallback(() => {
    setUpdatedJobIds(new Set())
  }, [])

  // Manual connect/disconnect for backwards compatibility
  const connect = useCallback(() => {
    if (!session?.accessToken) {
      console.warn('Cannot connect to WebSocket: No access token')
      return
    }
    // The service will automatically connect when there are subscribers
  }, [session?.accessToken])

  const disconnect = useCallback(() => {
    // The service will automatically disconnect when no subscribers remain
  }, [])

  // Set up WebSocket service subscription
  useEffect(() => {
    if (!session?.accessToken) {
      return
    }

    // Update token in service
    webSocketService.setToken(session.accessToken)

    // Subscribe to job updates
    const unsubscribe = webSocketService.subscribe('jobs')

    // Listen for status updates
    const handleStatusUpdate = (status: ConnectionStatus) => {
      setConnectionStatus(status)
    }

    // Listen for job update messages
    const handleMessage = (message: JobUpdateMessage) => {
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
    }

    webSocketService.on('jobs:status', handleStatusUpdate)
    webSocketService.on('jobs:message', handleMessage)

    // Set initial status
    setConnectionStatus(webSocketService.getConnectionStatus('jobs'))

    return () => {
      webSocketService.off('jobs:status', handleStatusUpdate)
      webSocketService.off('jobs:message', handleMessage)
      unsubscribe()
    }
  }, [session?.accessToken])

  return {
    connectionStatus,
    lastUpdate,
    updatedJobIds,
    connect,
    disconnect,
    clearUpdatedJobs
  }
}