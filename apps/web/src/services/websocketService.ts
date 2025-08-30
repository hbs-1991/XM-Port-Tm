'use client'

// Browser-compatible EventEmitter implementation
class EventEmitter {
  private events: Map<string, Function[]> = new Map()

  on(event: string, listener: Function) {
    if (!this.events.has(event)) {
      this.events.set(event, [])
    }
    this.events.get(event)!.push(listener)
  }

  off(event: string, listener: Function) {
    const listeners = this.events.get(event)
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index !== -1) {
        listeners.splice(index, 1)
      }
    }
  }

  emit(event: string, ...args: any[]) {
    const listeners = this.events.get(event)
    if (listeners) {
      listeners.forEach(listener => listener(...args))
    }
  }

  removeAllListeners() {
    this.events.clear()
  }

  setMaxListeners(n: number) {
    // No-op for browser compatibility
  }
}

// Message types
export interface JobUpdateMessage {
  type: 'job_update'
  data: {
    jobId: string
    status: 'completed' | 'processing' | 'failed' | 'pending'
    progress?: number
    completedAt?: string
    errorMessage?: string
    productsCount?: number
    confidenceScore?: number
  }
}

export interface ProcessingUpdateMessage {
  type: 'processing_update'
  job_id: string
  status: string
  progress: number
  message: string
  timestamp: number
  data?: Record<string, any>
}

export interface NotificationMessage {
  type: 'notification'
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  timestamp: number
}

export type WebSocketMessage = JobUpdateMessage | ProcessingUpdateMessage | NotificationMessage

export interface ConnectionStatus {
  connected: boolean
  reconnecting: boolean
  error: string | null
  lastConnected?: Date
  connectionCount: number
}

// WebSocket connection types
type WebSocketConnectionType = 'jobs' | 'processing'

interface WebSocketConnection {
  ws: WebSocket | null
  subscribers: number
  status: ConnectionStatus
  reconnectAttempts: number
  reconnectTimeout?: NodeJS.Timeout
}

class WebSocketService extends EventEmitter {
  private connections: Map<WebSocketConnectionType, WebSocketConnection> = new Map()
  private token: string | null = null
  private readonly maxReconnectAttempts = 5
  private readonly baseReconnectDelay = 1000
  private readonly maxReconnectDelay = 30000
  private isDestroyed = false
  private strictModeConnectionAttempts: Map<WebSocketConnectionType, number> = new Map()

  constructor() {
    super()
    this.setMaxListeners(100) // Allow more listeners for multiple components
  }

  setToken(token: string | null) {
    if (this.token !== token) {
      this.token = token
      // Reconnect all active connections with new token
      this.connections.forEach((connection, type) => {
        if (connection.subscribers > 0) {
          this.disconnect(type)
          this.connect(type)
        }
      })
    }
  }

  subscribe(connectionType: WebSocketConnectionType): () => void {
    const connection = this.getOrCreateConnection(connectionType)
    connection.subscribers++

    // Connect if not already connected
    if (!connection.ws || connection.ws.readyState === WebSocket.CLOSED) {
      // Small delay in development to avoid race conditions with hot reloading
      if (process.env.NODE_ENV === 'development') {
        setTimeout(() => this.connect(connectionType), 100)
      } else {
        this.connect(connectionType)
      }
    }

    // Return unsubscribe function
    return () => {
      this.unsubscribe(connectionType)
    }
  }

  private unsubscribe(connectionType: WebSocketConnectionType) {
    const connection = this.connections.get(connectionType)
    if (connection) {
      connection.subscribers = Math.max(0, connection.subscribers - 1)
      
      // Disconnect if no more subscribers
      if (connection.subscribers === 0) {
        this.disconnect(connectionType)
      }
    }
  }

  private getOrCreateConnection(connectionType: WebSocketConnectionType): WebSocketConnection {
    if (!this.connections.has(connectionType)) {
      this.connections.set(connectionType, {
        ws: null,
        subscribers: 0,
        status: {
          connected: false,
          reconnecting: false,
          error: null,
          connectionCount: 0
        },
        reconnectAttempts: 0
      })
    }
    return this.connections.get(connectionType)!
  }

  private connect(connectionType: WebSocketConnectionType) {
    if (this.isDestroyed) {
      return
    }

    if (!this.token) {
      console.warn('Cannot connect WebSocket: No access token')
      return
    }

    const connection = this.getOrCreateConnection(connectionType)
    
    // Don't create multiple connections
    if (connection.ws && connection.ws.readyState === WebSocket.CONNECTING) {
      return
    }

    if (connection.ws && connection.ws.readyState === WebSocket.OPEN) {
      return
    }

    // React StrictMode protection - limit rapid connection attempts
    const now = Date.now()
    const lastAttempt = this.strictModeConnectionAttempts.get(connectionType) || 0
    if (now - lastAttempt < 500) { // Increased debounce for development stability
      if (process.env.NODE_ENV === 'development') {
        console.log(`⏳ Debouncing ${connectionType} WebSocket connection (development mode)`)
      }
      return
    }
    this.strictModeConnectionAttempts.set(connectionType, now)

    try {
      // Close existing connection if any
      if (connection.ws) {
        connection.ws.close()
      }

      const wsUrl = this.getWebSocketUrl(connectionType)
      if (process.env.NODE_ENV === 'development') {
        console.log(`🔌 Connecting to ${connectionType} WebSocket...`)
      }
      
      connection.status = {
        ...connection.status,
        reconnecting: true,
        error: null
      }
      this.emit(`${connectionType}:status`, connection.status)

      const ws = new WebSocket(wsUrl)
      connection.ws = ws

      ws.onopen = () => {
        if (process.env.NODE_ENV === 'development') {
          console.log(`✅ ${connectionType} WebSocket connected successfully`)
        }
        connection.status = {
          connected: true,
          reconnecting: false,
          error: null,
          lastConnected: new Date(),
          connectionCount: connection.status.connectionCount + 1
        }
        connection.reconnectAttempts = 0
        this.emit(`${connectionType}:status`, connection.status)

        // Send ping to keep connection alive
        this.sendMessage(connectionType, { type: 'ping' })
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.emit(`${connectionType}:message`, message)
        } catch (error) {
          console.warn(`Invalid WebSocket message format from ${connectionType}:`, event.data.substring(0, 100) + '...')
        }
      }

      ws.onerror = (event) => {
        // Only log errors in production or when verbose logging is enabled
        if (process.env.NODE_ENV === 'production' || process.env.VERBOSE_WS_LOGS) {
          console.error(`${connectionType} WebSocket error:`, {
            readyState: ws.readyState,
            url: ws.url,
            timestamp: new Date().toISOString()
          })
        }
        
        connection.status = {
          ...connection.status,
          error: `Connection error at ${new Date().toLocaleTimeString()}`
        }
        this.emit(`${connectionType}:status`, connection.status)
      }

      ws.onclose = (event) => {
        const wasIntentional = event.code === 1000
        console.log(`${connectionType} WebSocket closed:`, {
          code: event.code,
          reason: event.reason || 'No reason provided',
          wasClean: event.wasClean,
          intentional: wasIntentional,
          reconnectAttempts: connection.reconnectAttempts
        })

        connection.status = {
          ...connection.status,
          connected: false,
          reconnecting: false
        }
        connection.ws = null
        this.emit(`${connectionType}:status`, connection.status)

        // Auto-reconnect if not intentional and has subscribers
        if (!wasIntentional && connection.subscribers > 0 && connection.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect(connectionType)
        } else if (connection.reconnectAttempts >= this.maxReconnectAttempts) {
          connection.status.error = 'Max reconnection attempts reached'
          this.emit(`${connectionType}:status`, connection.status)
        }
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      console.error(`Failed to create ${connectionType} WebSocket:`, errorMessage)
      
      connection.status = {
        ...connection.status,
        reconnecting: false,
        error: `Failed to connect: ${errorMessage}`
      }
      this.emit(`${connectionType}:status`, connection.status)
    }
  }

  private scheduleReconnect(connectionType: WebSocketConnectionType) {
    const connection = this.connections.get(connectionType)
    if (!connection) return

    connection.reconnectAttempts++
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, connection.reconnectAttempts - 1),
      this.maxReconnectDelay
    )

    console.log(`Scheduling ${connectionType} reconnect in ${delay}ms (attempt ${connection.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    connection.status.reconnecting = true
    this.emit(`${connectionType}:status`, connection.status)

    connection.reconnectTimeout = setTimeout(() => {
      if (connection.subscribers > 0) {
        this.connect(connectionType)
      }
    }, delay)
  }

  private disconnect(connectionType: WebSocketConnectionType) {
    const connection = this.connections.get(connectionType)
    if (!connection) return

    // Clear reconnect timeout
    if (connection.reconnectTimeout) {
      clearTimeout(connection.reconnectTimeout)
      connection.reconnectTimeout = undefined
    }

    // Close WebSocket connection
    if (connection.ws) {
      console.log(`Disconnecting ${connectionType} WebSocket`)
      connection.ws.close(1000, 'Manual disconnect')
      connection.ws = null
    }

    connection.status = {
      connected: false,
      reconnecting: false,
      error: null,
      connectionCount: connection.status.connectionCount
    }
    connection.reconnectAttempts = 0
    this.emit(`${connectionType}:status`, connection.status)
  }

  private getWebSocketUrl(connectionType: WebSocketConnectionType): string {
    const backendHost = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    
    const endpoint = connectionType === 'jobs' ? 'jobs' : 'processing-updates'
    return `${protocol}//${backendHost}/api/v1/ws/${endpoint}?token=${encodeURIComponent(this.token!)}`
  }

  sendMessage(connectionType: WebSocketConnectionType, message: any) {
    const connection = this.connections.get(connectionType)
    if (connection?.ws?.readyState === WebSocket.OPEN) {
      connection.ws.send(JSON.stringify(message))
    }
  }

  getConnectionStatus(connectionType: WebSocketConnectionType): ConnectionStatus {
    const connection = this.connections.get(connectionType)
    return connection?.status || {
      connected: false,
      reconnecting: false,
      error: null,
      connectionCount: 0
    }
  }

  // Cleanup method
  destroy() {
    this.isDestroyed = true
    this.connections.forEach((_, type) => {
      this.disconnect(type)
    })
    this.connections.clear()
    this.strictModeConnectionAttempts.clear()
    this.removeAllListeners()
  }
}

// Singleton instance
export const webSocketService = new WebSocketService()

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    webSocketService.destroy()
  })
}