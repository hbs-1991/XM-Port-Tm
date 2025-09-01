import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import NotificationCenter from '@/components/shared/NotificationCenter'
import { WebSocketNotification } from '@/hooks/useProcessingUpdates'

describe('NotificationCenter', () => {
  const mockClearNotifications = jest.fn()

  const sampleNotifications: WebSocketNotification[] = [
    {
      type: 'notification',
      level: 'success',
      message: 'File processed successfully',
      timestamp: Date.now() - 1000
    },
    {
      type: 'notification',
      level: 'error',
      message: 'Processing failed due to invalid format',
      timestamp: Date.now() - 2000
    },
    {
      type: 'notification',
      level: 'warning',
      message: 'Low credit balance detected',
      timestamp: Date.now() - 3000
    },
    {
      type: 'notification',
      level: 'info',
      message: 'New features available in dashboard',
      timestamp: Date.now() - 4000
    }
  ]

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render connection status badge when connected', () => {
    render(
      <NotificationCenter
        notifications={[]}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    expect(screen.getByText('Live Updates Active')).toBeInTheDocument()
    const badge = screen.getByText('Live Updates Active').closest('div')
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('should render connection status badge when disconnected', () => {
    render(
      <NotificationCenter
        notifications={[]}
        onClearNotifications={mockClearNotifications}
        isConnected={false}
        connectionStatus="disconnected"
      />
    )

    expect(screen.getByText('Disconnected')).toBeInTheDocument()
    const badge = screen.getByText('Disconnected').closest('div')
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800')
  })

  it('should render connection status badge when connecting', () => {
    render(
      <NotificationCenter
        notifications={[]}
        onClearNotifications={mockClearNotifications}
        isConnected={false}
        connectionStatus="connecting"
      />
    )

    expect(screen.getByText('Connecting...')).toBeInTheDocument()
    const badge = screen.getByText('Connecting...').closest('div')
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800')
  })

  it('should render connection status badge when error', () => {
    render(
      <NotificationCenter
        notifications={[]}
        onClearNotifications={mockClearNotifications}
        isConnected={false}
        connectionStatus="error"
      />
    )

    expect(screen.getByText('Connection Error')).toBeInTheDocument()
    const badge = screen.getByText('Connection Error').closest('div')
    expect(badge).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('should not render notifications panel when no notifications', () => {
    render(
      <NotificationCenter
        notifications={[]}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    expect(screen.queryByText('Recent Updates')).not.toBeInTheDocument()
  })

  it('should render notifications panel when notifications exist', () => {
    render(
      <NotificationCenter
        notifications={sampleNotifications.slice(0, 2)}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    expect(screen.getByText('Recent Updates')).toBeInTheDocument()
    expect(screen.getByText('2 notifications')).toBeInTheDocument()
  })

  it('should render singular notification text for single notification', () => {
    render(
      <NotificationCenter
        notifications={[sampleNotifications[0]]}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    expect(screen.getByText('1 notification')).toBeInTheDocument()
  })

  it('should display notification messages with correct styling', () => {
    render(
      <NotificationCenter
        notifications={sampleNotifications}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    // Check success notification
    expect(screen.getByText('File processed successfully')).toBeInTheDocument()
    expect(screen.getByText('Success')).toBeInTheDocument()

    // Check error notification
    expect(screen.getByText('Processing failed due to invalid format')).toBeInTheDocument()
    expect(screen.getByText('Error')).toBeInTheDocument()

    // Check warning notification
    expect(screen.getByText('Low credit balance detected')).toBeInTheDocument()
    expect(screen.getByText('Warning')).toBeInTheDocument()

    // Check info notification
    expect(screen.getByText('New features available in dashboard')).toBeInTheDocument()
    expect(screen.getByText('Info')).toBeInTheDocument()
  })

  it('should display only 5 notifications maximum', () => {
    const manyNotifications: WebSocketNotification[] = Array.from({ length: 8 }, (_, i) => ({
      type: 'notification',
      level: 'info' as const,
      message: `Notification ${i + 1}`,
      timestamp: Date.now() - i * 1000
    }))

    render(
      <NotificationCenter
        notifications={manyNotifications}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    // Should show first 5 notifications
    expect(screen.getByText('Notification 1')).toBeInTheDocument()
    expect(screen.getByText('Notification 5')).toBeInTheDocument()

    // Should not show 6th notification
    expect(screen.queryByText('Notification 6')).not.toBeInTheDocument()

    // Should show "and X more" message
    expect(screen.getByText('and 3 more...')).toBeInTheDocument()
  })

  it('should call onClearNotifications when clear button is clicked', () => {
    render(
      <NotificationCenter
        notifications={sampleNotifications}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    const clearButton = screen.getByRole('button')
    fireEvent.click(clearButton)

    expect(mockClearNotifications).toHaveBeenCalledTimes(1)
  })

  it('should format timestamps correctly', () => {
    // Use a specific timestamp that will produce a predictable time format
    const now = new Date('2023-12-15T13:30:45.123Z')
    const notification: WebSocketNotification = {
      type: 'notification',
      level: 'info',
      message: 'Test message',
      timestamp: now.getTime()
    }

    render(
      <NotificationCenter
        notifications={[notification]}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    // Check that some time format is displayed (the exact format depends on locale)
    expect(screen.getByText(/\d{2}:\d{2}:\d{2}/)).toBeInTheDocument()
  })

  it('should have proper accessibility attributes', () => {
    render(
      <NotificationCenter
        notifications={sampleNotifications}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    // Clear button should be accessible
    const clearButton = screen.getByRole('button')
    expect(clearButton).toBeInTheDocument()

    // Notification content should be readable
    expect(screen.getByText('Recent Updates')).toBeInTheDocument()
  })

  it('should handle notification level styling correctly', () => {
    const levelTestNotifications: WebSocketNotification[] = [
      {
        type: 'notification',
        level: 'success',
        message: 'Success message',
        timestamp: Date.now()
      },
      {
        type: 'notification',
        level: 'error',
        message: 'Error message',
        timestamp: Date.now()
      }
    ]

    const { container } = render(
      <NotificationCenter
        notifications={levelTestNotifications}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    // Check for success styling classes
    expect(container.querySelector('.bg-green-50')).toBeInTheDocument()
    expect(container.querySelector('.text-green-800')).toBeInTheDocument()

    // Check for error styling classes
    expect(container.querySelector('.bg-red-50')).toBeInTheDocument()
    expect(container.querySelector('.text-red-800')).toBeInTheDocument()
  })

  it('should handle empty notification message gracefully', () => {
    const notificationWithEmptyMessage: WebSocketNotification = {
      type: 'notification',
      level: 'info',
      message: '',
      timestamp: Date.now()
    }

    render(
      <NotificationCenter
        notifications={[notificationWithEmptyMessage]}
        onClearNotifications={mockClearNotifications}
        isConnected={true}
        connectionStatus="connected"
      />
    )

    // Should still render the notification structure
    expect(screen.getByText('Info')).toBeInTheDocument()
    // Empty message should still create the container
    expect(screen.getByText('Recent Updates')).toBeInTheDocument()
  })
})