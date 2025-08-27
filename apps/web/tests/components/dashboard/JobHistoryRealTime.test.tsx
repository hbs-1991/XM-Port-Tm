import { render, screen, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import JobHistory from '@/components/dashboard/JobHistory'
import { useProcessingUpdates } from '@/hooks/useProcessingUpdates'
import { ProcessingJob, ProcessingStatus } from '@shared/types/processing'

// Mock the useProcessingUpdates hook
jest.mock('@/hooks/useProcessingUpdates')
const mockUseProcessingUpdates = useProcessingUpdates as jest.MockedFunction<typeof useProcessingUpdates>

// Mock fetch
global.fetch = jest.fn()
const mockFetch = fetch as jest.MockedFunction<typeof fetch>

describe('JobHistory Real-time Updates', () => {
  const sampleJobs: ProcessingJob[] = [
    {
      id: 'job-1',
      input_file_name: 'test-file-1.csv',
      input_file_size: 1024,
      status: ProcessingStatus.PROCESSING,
      country_schema: 'TM',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      processing_time_ms: undefined,
      credits_used: 10,
      total_products: 100,
      successful_matches: 0,
      average_confidence: undefined,
      has_xml_output: false,
      xml_generation_status: 'PENDING'
    },
    {
      id: 'job-2',
      input_file_name: 'test-file-2.csv',
      input_file_size: 2048,
      status: ProcessingStatus.COMPLETED,
      country_schema: 'TM',
      created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
      processing_time_ms: 5000,
      credits_used: 15,
      total_products: 50,
      successful_matches: 48,
      average_confidence: 0.95,
      has_xml_output: true,
      xml_generation_status: 'COMPLETED'
    }
  ]

  const mockResponse = {
    jobs: sampleJobs,
    pagination: {
      page: 1,
      limit: 50,
      total_count: 2,
      total_pages: 1,
      has_next: false,
      has_prev: false
    },
    filters: {}
  }

  beforeEach(() => {
    jest.clearAllMocks()

    // Default mock for useProcessingUpdates
    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: null,
      isConnected: true,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected'
    })

    // Default mock for fetch
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockResponse
    } as Response)
  })

  it('should show live indicator for connected state', async () => {
    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('Live Updates')).toBeInTheDocument()
    })

    expect(screen.getByText('Live Updates')).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('should show offline indicator when disconnected', async () => {
    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: null,
      isConnected: false,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'disconnected'
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('Offline')).toBeInTheDocument()
    })

    expect(screen.getByText('Offline')).toHaveClass('bg-gray-100', 'text-gray-600')
  })

  it('should highlight active jobs with live indicator', async () => {
    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test-file-1.csv')).toBeInTheDocument()
    })

    // Processing job should have live indicator
    const processingJobRow = screen.getByText('test-file-1.csv').closest('tr')
    expect(processingJobRow).toHaveClass('bg-blue-50/30')
    expect(screen.getByText('• Live')).toBeInTheDocument()

    // Completed job should not have live indicator
    const completedJobRow = screen.getByText('test-file-2.csv').closest('tr')
    expect(completedJobRow).not.toHaveClass('bg-blue-50/30')
  })

  it('should update job status in real-time', async () => {
    const { rerender } = render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('PROCESSING')).toBeInTheDocument()
    })

    // Mock WebSocket message for job completion
    const processingUpdate = {
      type: 'processing_update' as const,
      job_id: 'job-1',
      status: 'COMPLETED',
      progress: 100,
      message: 'Processing completed successfully',
      timestamp: Date.now(),
      data: {
        processing_time_ms: 3000,
        has_xml_output: true,
        xml_generation_status: 'COMPLETED',
        total_products: 100,
        successful_matches: 98,
        average_confidence: 0.92
      }
    }

    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: processingUpdate,
      isConnected: true,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected'
    })

    rerender(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    })

    // Should no longer show live indicator for this job
    expect(screen.queryByText('• Live')).not.toBeInTheDocument()

    // Should show updated statistics
    expect(screen.getByText('98/100')).toBeInTheDocument()
    expect(screen.getByText('92% avg')).toBeInTheDocument()
  })

  it('should show spinning loader for processing jobs when connected', async () => {
    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('PROCESSING')).toBeInTheDocument()
    })

    // Should show spinning loader
    const processingBadge = screen.getByText('PROCESSING').closest('.flex')
    expect(processingBadge?.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('should show offline indicator for active jobs when disconnected', async () => {
    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: null,
      isConnected: false,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'disconnected'
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('PROCESSING')).toBeInTheDocument()
    })

    // Should show offline indicator for active job
    expect(screen.getByText('(offline)')).toBeInTheDocument()
  })

  it('should handle job not in current list gracefully', async () => {
    const { rerender } = render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test-file-1.csv')).toBeInTheDocument()
    })

    // Mock update for a job not in the current list
    const updateForUnknownJob = {
      type: 'processing_update' as const,
      job_id: 'unknown-job',
      status: 'COMPLETED',
      progress: 100,
      message: 'Processing completed',
      timestamp: Date.now()
    }

    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: updateForUnknownJob,
      isConnected: true,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected'
    })

    rerender(<JobHistory />)

    // Should not crash and should maintain existing jobs
    await waitFor(() => {
      expect(screen.getByText('test-file-1.csv')).toBeInTheDocument()
      expect(screen.getByText('test-file-2.csv')).toBeInTheDocument()
    })
  })

  it('should handle non-processing-update messages gracefully', async () => {
    const { rerender } = render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test-file-1.csv')).toBeInTheDocument()
    })

    // Mock a different type of WebSocket message
    const notificationMessage = {
      type: 'notification' as const,
      level: 'info' as const,
      message: 'System maintenance scheduled',
      timestamp: Date.now()
    }

    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: notificationMessage,
      isConnected: true,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected'
    })

    rerender(<JobHistory />)

    // Should not update job statuses
    await waitFor(() => {
      expect(screen.getByText('PROCESSING')).toBeInTheDocument()
      expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    })
  })

  it('should update multiple job fields from WebSocket data', async () => {
    const { rerender } = render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('0/100')).toBeInTheDocument() // Initial state
    })

    // Mock comprehensive update
    const comprehensiveUpdate = {
      type: 'processing_update' as const,
      job_id: 'job-1',
      status: 'COMPLETED',
      progress: 100,
      message: 'All products processed successfully',
      timestamp: Date.now(),
      data: {
        processing_time_ms: 4500,
        has_xml_output: true,
        xml_generation_status: 'COMPLETED',
        total_products: 100,
        successful_matches: 95,
        average_confidence: 0.88
      }
    }

    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: comprehensiveUpdate,
      isConnected: true,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected'
    })

    rerender(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument()
      expect(screen.getByText('95/100')).toBeInTheDocument()
      expect(screen.getByText('88% avg')).toBeInTheDocument()
    })

    // Processing time should be updated
    expect(screen.getByText('4.5s')).toBeInTheDocument()
  })

  it('should preserve existing job data when partial updates are received', async () => {
    const { rerender } = render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test-file-1.csv')).toBeInTheDocument()
    })

    // Mock partial update (only status change)
    const partialUpdate = {
      type: 'processing_update' as const,
      job_id: 'job-1',
      status: 'COMPLETED',
      progress: 100,
      message: 'Processing completed',
      timestamp: Date.now()
      // No data field - should preserve existing job data
    }

    mockUseProcessingUpdates.mockReturnValue({
      lastMessage: partialUpdate,
      isConnected: true,
      notifications: [],
      sendMessage: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected'
    })

    rerender(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    })

    // Should preserve original file name and other data
    expect(screen.getByText('test-file-1.csv')).toBeInTheDocument()
    expect(screen.getByText('1 KB • TM')).toBeInTheDocument()
  })
})