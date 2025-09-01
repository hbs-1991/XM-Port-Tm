'use client'

import { createContext, useContext, useEffect, ReactNode } from 'react'
import { useSession } from 'next-auth/react'
import { webSocketService } from '../../services/websocketService'

interface WebSocketContextType {
  // Context could be extended with shared WebSocket state if needed
}

const WebSocketContext = createContext<WebSocketContextType>({})

interface WebSocketProviderProps {
  children: ReactNode
}

/**
 * Provides global WebSocket service management
 * Handles authentication token updates and service lifecycle
 */
export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const { data: session } = useSession()

  // Update WebSocket service token when session changes
  useEffect(() => {
    if (session?.accessToken) {
      webSocketService.setToken(session.accessToken)
    } else {
      webSocketService.setToken(null)
    }
  }, [session?.accessToken])

  // Cleanup service on unmount
  useEffect(() => {
    return () => {
      // Note: Don't destroy the service on unmount as it's a singleton
      // that may be used by other components. Only clean up on page unload.
    }
  }, [])

  return (
    <WebSocketContext.Provider value={{}}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocketContext = () => useContext(WebSocketContext)