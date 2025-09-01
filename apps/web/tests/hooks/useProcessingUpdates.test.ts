import { renderHook, act, waitFor } from '@testing-library/react'
import { useProcessingUpdates, ProcessingUpdate, WebSocketNotification } from '@/hooks/useProcessingUpdates'
import { useSession } from 'next-auth/react'

// Mock useSession hook
jest.mock('next-auth/react')
const mockUseSession = useSession as jest.MockedFunction<typeof useSession>

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  url: string
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 100)
  }

  send(data: string) {
    // Mock send - no-op for testing
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }))
    }
  }

  // Helper method for testing
  simulateMessage(data: any) {
    if (this.onmessage && this.readyState === MockWebSocket.OPEN) {
      this.onmessage(new MessageEvent('message', { 
        data: JSON.stringify(data) 
      }))
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }
}

// Replace global WebSocket with mock
const originalWebSocket = global.WebSocket
let mockWebSocketInstance: MockWebSocket | null = null

beforeEach(() => {
  global.WebSocket = jest.fn().mockImplementation((url: string) => {
    mockWebSocketInstance = new MockWebSocket(url)
    return mockWebSocketInstance
  }) as any

  mockUseSession.mockReturnValue({
    data: {
      user: { id: '1', email: 'test@example.com', role: 'USER' },
      accessToken: 'mock-token',
      refreshToken: 'mock-refresh-token',
      expires: '2024-01-01'
    },
    status: 'authenticated',
    update: jest.fn()
  })

  jest.clearAllMocks()
})

afterEach(() => {
  global.WebSocket = originalWebSocket
  mockWebSocketInstance = null
})

describe('useProcessingUpdates', () => {
  it('should initialize with default state', () => {
    const { result } = renderHook(() => useProcessingUpdates())

    expect(result.current.isConnected).toBe(false)
    expect(result.current.lastMessage).toBeNull()
    expect(result.current.notifications).toEqual([])
    expect(result.current.connectionStatus).toBe('disconnected')
  })

  it('should not connect when no token is available', () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: 'unauthenticated',
      update: jest.fn()
    })

    const { result } = renderHook(() => useProcessingUpdates())

    expect(result.current.connectionStatus).toBe('disconnected')
    expect(global.WebSocket).not.toHaveBeenCalled()
  })

  it('should establish WebSocket connection when token is available', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    expect(global.WebSocket).toHaveBeenCalledWith(
      expect.stringContaining('ws://localhost:8000/ws/processing-updates?token=mock-token')
    )
    expect(result.current.connectionStatus).toBe('connecting')

    // Wait for connection to be established
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    expect(result.current.connectionStatus).toBe('connected')
  })

  it('should handle processing updates', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    // Wait for connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate receiving a processing update
    const processingUpdate: ProcessingUpdate = {
      type: 'processing_update',
      job_id: 'test-job-id',
      status: 'COMPLETED',
      progress: 100,
      message: 'Processing completed successfully',
      timestamp: Date.now()
    }

    act(() => {
      mockWebSocketInstance?.simulateMessage(processingUpdate)
    })

    expect(result.current.lastMessage).toEqual(processingUpdate)
    expect(result.current.notifications).toHaveLength(1)
    expect(result.current.notifications[0]).toMatchObject({
      type: 'notification',
      level: 'success',
      message: 'Processing completed successfully'
    })
  })

  it('should handle different status levels in notifications', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Test failed status
    act(() => {
      mockWebSocketInstance?.simulateMessage({
        type: 'processing_update',
        job_id: 'test-job-1',
        status: 'FAILED',
        progress: 0,
        message: 'Processing failed',
        timestamp: Date.now()
      })
    })

    expect(result.current.notifications[0].level).toBe('error')

    // Test processing status
    act(() => {
      mockWebSocketInstance?.simulateMessage({
        type: 'processing_update',
        job_id: 'test-job-2',
        status: 'PROCESSING',
        progress: 50,
        message: 'Processing in progress',
        timestamp: Date.now()
      })
    })

    expect(result.current.notifications[0].level).toBe('info')
  })

  it('should handle direct notifications', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    const notification: WebSocketNotification = {
      type: 'notification',
      level: 'warning',
      message: 'System maintenance in 5 minutes',
      timestamp: Date.now()
    }

    act(() => {
      mockWebSocketInstance?.simulateMessage(notification)
    })

    expect(result.current.notifications).toHaveLength(1)
    expect(result.current.notifications[0]).toEqual(notification)
  })

  it('should limit notifications to 10', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Send 15 notifications
    for (let i = 0; i < 15; i++) {
      act(() => {
        mockWebSocketInstance?.simulateMessage({
          type: 'processing_update',
          job_id: `job-${i}`,
          status: 'COMPLETED',
          progress: 100,
          message: `Job ${i} completed`,
          timestamp: Date.now() + i
        })
      })
    }

    // Should only keep the latest 10
    expect(result.current.notifications).toHaveLength(10)
    expect(result.current.notifications[0].message).toBe('Job 14 completed')
    expect(result.current.notifications[9].message).toBe('Job 5 completed')
  })

  it('should clear notifications', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Add some notifications
    act(() => {
      mockWebSocketInstance?.simulateMessage({
        type: 'processing_update',
        job_id: 'test-job',
        status: 'COMPLETED',
        progress: 100,
        message: 'Job completed',
        timestamp: Date.now()
      })
    })

    expect(result.current.notifications).toHaveLength(1)

    // Clear notifications
    act(() => {
      result.current.clearNotifications()
    })

    expect(result.current.notifications).toHaveLength(0)
  })

  it('should handle connection errors', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate connection error
    act(() => {
      mockWebSocketInstance?.simulateError()
    })

    expect(result.current.connectionStatus).toBe('error')
  })

  it('should attempt reconnection on connection loss', async () => {
    const { result } = renderHook(() => useProcessingUpdates({
      autoReconnect: true,
      reconnectDelay: 100,
      maxReconnectAttempts: 2
    }))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate connection close
    act(() => {
      mockWebSocketInstance?.close(1000, 'Normal closure')
    })

    expect(result.current.isConnected).toBe(false)
    expect(result.current.connectionStatus).toBe('connecting')

    // Should attempt to reconnect
    await waitFor(() => {
      expect(global.WebSocket).toHaveBeenCalledTimes(2)
    }, { timeout: 500 })
  })

  it('should send messages when connected', async () => {
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    const sendSpy = jest.spyOn(mockWebSocketInstance!, 'send')
    
    act(() => {
      result.current.sendMessage({ type: 'test', data: 'hello' })
    })

    expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({ type: 'test', data: 'hello' }))
  })

  it('should handle malformed messages gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
    const { result } = renderHook(() => useProcessingUpdates())

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Send malformed JSON
    act(() => {
      if (mockWebSocketInstance?.onmessage) {
        mockWebSocketInstance.onmessage(new MessageEvent('message', { 
          data: 'invalid json{' 
        }))
      }
    })

    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to parse WebSocket message:',
      expect.any(Error)
    )

    // State should remain unchanged
    expect(result.current.lastMessage).toBeNull()
    expect(result.current.notifications).toHaveLength(0)

    consoleSpy.mockRestore()
  })
})