/**
 * JobHistory component tests
 */
import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProcessingStatus } from '@shared/types/processing'
import JobHistory from '@/components/dashboard/JobHistory'

// Mock fetch
const mockFetch = jest.fn()
global.fetch = mockFetch

// Mock date-fns format function
jest.mock('date-fns', () => ({
  format: (date: Date | string, formatStr: string) => {
    const d = new Date(date)
    if (formatStr === 'MMM dd, yyyy') return 'Jan 01, 2024'
    if (formatStr === 'HH:mm') return '10:30'
    return d.toString()
  }
}))

// Mock data
const mockJobs = [
  {
    id: '1',
    input_file_name: 'products.csv',
    status: ProcessingStatus.COMPLETED,
    input_file_size: 1024000,
    country_schema: 'USA',
    credits_used: 5,
    total_products: 100,
    successful_matches: 95,
    average_confidence: 0.85,
    processing_time_ms: 45000,
    has_xml_output: true,
    xml_generation_status: 'COMPLETED',
    created_at: '2024-01-01T10:30:00Z',
    started_at: '2024-01-01T10:31:00Z',
    completed_at: '2024-01-01T10:31:45Z',
  },
  {
    id: '2',
    input_file_name: 'inventory.xlsx',
    status: ProcessingStatus.PROCESSING,
    input_file_size: 512000,
    country_schema: 'CAN',
    credits_used: 3,
    total_products: 50,
    successful_matches: 0,
    processing_time_ms: null,
    has_xml_output: false,
    created_at: '2024-01-01T09:15:00Z',
    started_at: '2024-01-01T09:16:00Z',
  },
  {
    id: '3',
    input_file_name: 'export_data.csv',
    status: ProcessingStatus.FAILED,
    input_file_size: 2048000,
    country_schema: 'GBR',
    credits_used: 0,
    total_products: 200,
    successful_matches: 0,
    processing_time_ms: 5000,
    has_xml_output: false,
    error_message: 'File format validation failed',
    created_at: '2024-01-01T08:00:00Z',
    started_at: '2024-01-01T08:01:00Z',
    completed_at: '2024-01-01T08:01:05Z',
  }
]

const mockApiResponse = {
  jobs: mockJobs,
  pagination: {
    page: 1,
    limit: 50,
    total_count: 3,
    total_pages: 1,
    has_next: false,
    has_prev: false
  },
  filters: {
    search: '',
    status: '',
    date_from: '',
    date_to: ''
  }
}

describe('JobHistory Component', () => {
  beforeEach(() => {
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockApiResponse)
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    render(<JobHistory />)
    
    expect(screen.getByText('Loading processing history...')).toBeInTheDocument()
    expect(screen.getByLabelText('Loading')).toBeInTheDocument()
  })

  it('renders job history table with data', async () => {
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Processing History')).toBeInTheDocument()
    })
    
    // Check table headers
    expect(screen.getByText('File Name')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Date')).toBeInTheDocument()
    expect(screen.getByText('Processing Time')).toBeInTheDocument()
    expect(screen.getByText('Products')).toBeInTheDocument()
    expect(screen.getByText('Credits')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
    
    // Check job data
    expect(screen.getByText('products.csv')).toBeInTheDocument()
    expect(screen.getByText('inventory.xlsx')).toBeInTheDocument()
    expect(screen.getByText('export_data.csv')).toBeInTheDocument()
    
    // Check status badges
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('displays correct file information', async () => {
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('1000 KB • USA')).toBeInTheDocument()
    })
    
    expect(screen.getByText('500 KB • CAN')).toBeInTheDocument()
    expect(screen.getByText('2 MB • GBR')).toBeInTheDocument()
  })

  it('displays correct processing statistics', async () => {
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('95/100')).toBeInTheDocument()
      expect(screen.getByText('85% avg')).toBeInTheDocument()
    })
    
    expect(screen.getByText('0/50')).toBeInTheDocument()
    expect(screen.getByText('0/200')).toBeInTheDocument()
  })

  it('formats processing time correctly', async () => {
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('45.0s')).toBeInTheDocument()
    })
    
    expect(screen.getByText('N/A')).toBeInTheDocument() // For processing job
    expect(screen.getByText('5.0s')).toBeInTheDocument() // For failed job
  })

  it('shows download button only for completed jobs with XML output', async () => {
    render(<JobHistory />)
    
    await waitFor(() => {
      const downloadButtons = screen.getAllByRole('button', { name: /download/i })
      expect(downloadButtons).toHaveLength(1)
    })
  })

  it('handles search functionality', async () => {
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search by file name...')).toBeInTheDocument()
    })
    
    const searchInput = screen.getByPlaceholderText('Search by file name...')
    const applyButton = screen.getByText('Apply Filters')
    
    await user.type(searchInput, 'products')
    await user.click(applyButton)
    
    expect(mockFetch).toHaveBeenLastCalledWith(
      expect.stringContaining('search=products'),
      expect.any(Object)
    )
  })

  it('handles status filtering', async () => {
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Processing History')).toBeInTheDocument()
    })
    
    const statusSelects = screen.getAllByText('All statuses')
    const statusSelect = statusSelects[0]
    await user.click(statusSelect)
    
    await waitFor(() => {
      const completedOptions = screen.getAllByText('Completed')
      expect(completedOptions.length).toBeGreaterThan(0)
    })
    
    const completedOptions = screen.getAllByText('Completed')
    // Find the option, not the badge
    const completedOption = completedOptions.find(el => 
      el.getAttribute('data-radix-collection-item') !== null ||
      el.closest('[role="option"]') !== null
    )
    
    if (completedOption) {
      await user.click(completedOption)
      
      const applyButton = screen.getByText('Apply Filters')
      await user.click(applyButton)
      
      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.stringContaining('status=COMPLETED'),
        expect.any(Object)
      )
    }
  })

  it('handles date range filtering', async () => {
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      const dateInputs = screen.getAllByDisplayValue('')
      expect(dateInputs.length).toBeGreaterThan(0)
    })
    
    const dateFromInputs = screen.getAllByDisplayValue('')
    const dateFromInput = dateFromInputs.find(input => 
      input.getAttribute('type') === 'date'
    ) as HTMLInputElement
    
    if (dateFromInput) {
      await user.type(dateFromInput, '2024-01-01')
      
      const applyButton = screen.getByText('Apply Filters')
      await user.click(applyButton)
      
      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.stringContaining('date_from=2024-01-01'),
        expect.any(Object)
      )
    }
  })

  it('handles pagination', async () => {
    const paginatedResponse = {
      ...mockApiResponse,
      pagination: {
        ...mockApiResponse.pagination,
        total_pages: 3,
        has_next: true,
        has_prev: false
      }
    }
    
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(paginatedResponse)
    })
    
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    })
    
    const nextButton = screen.getByText('Next')
    expect(nextButton).toBeEnabled()
    
    const prevButton = screen.getByText('Previous')
    expect(prevButton).toBeDisabled()
    
    await user.click(nextButton)
    
    expect(mockFetch).toHaveBeenLastCalledWith(
      expect.stringContaining('page=2'),
      expect.any(Object)
    )
  })

  it('clears filters correctly', async () => {
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Clear Filters')).toBeInTheDocument()
    })
    
    // Set some filter values
    const searchInput = screen.getByPlaceholderText('Search by file name...')
    await user.type(searchInput, 'test')
    
    // Clear filters
    const clearButton = screen.getByText('Clear Filters')
    await user.click(clearButton)
    
    expect(searchInput).toHaveValue('')
    expect(mockFetch).toHaveBeenLastCalledWith(
      expect.not.stringContaining('search='),
      expect.any(Object)
    )
  })

  it('handles API errors gracefully', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'API Error' })
    })
    
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Error loading jobs')).toBeInTheDocument()
      expect(screen.getByText('API Error')).toBeInTheDocument()
    })
    
    expect(screen.getByText('Try Again')).toBeInTheDocument()
  })

  it('handles network errors', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))
    
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Error loading jobs')).toBeInTheDocument()
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('shows empty state when no jobs found', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ...mockApiResponse,
        jobs: []
      })
    })
    
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('No processing jobs found')).toBeInTheDocument()
    })
  })

  it('shows filtered empty state message', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ...mockApiResponse,
        jobs: [],
        filters: { search: 'test', status: '', date_from: '', date_to: '' }
      })
    })
    
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('No processing jobs found')).toBeInTheDocument()
      expect(screen.getByText('Try adjusting your filters or clearing them to see more results')).toBeInTheDocument()
    })
  })

  it('handles file download', async () => {
    // Mock URL.createObjectURL and related methods
    const mockCreateObjectURL = jest.fn(() => 'mock-url')
    const mockRevokeObjectURL = jest.fn()
    const mockClick = jest.fn()
    
    global.URL.createObjectURL = mockCreateObjectURL
    global.URL.revokeObjectURL = mockRevokeObjectURL
    
    // Mock document methods
    const mockAppendChild = jest.fn()
    const mockRemoveChild = jest.fn()
    const mockCreateElement = jest.fn(() => ({
      href: '',
      download: '',
      click: mockClick
    }))
    
    document.appendChild = mockAppendChild
    document.removeChild = mockRemoveChild
    document.createElement = mockCreateElement
    
    // Mock download response
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      })
      .mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.resolve(new Blob(['xml content']))
      })
    
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      const downloadButton = screen.getByRole('button', { name: /download/i })
      expect(downloadButton).toBeInTheDocument()
    })
    
    const downloadButton = screen.getByRole('button', { name: /download/i })
    await user.click(downloadButton)
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenLastCalledWith(
        '/api/proxy/xml-generation/1/download',
        expect.objectContaining({
          credentials: 'include'
        })
      )
    })
  })

  it('handles download errors', async () => {
    // Mock window.alert
    const mockAlert = jest.fn()
    global.alert = mockAlert
    
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      })
      .mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Download failed' })
      })
    
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      const downloadButton = screen.getByRole('button', { name: /download/i })
      expect(downloadButton).toBeInTheDocument()
    })
    
    const downloadButton = screen.getByRole('button', { name: /download/i })
    await user.click(downloadButton)
    
    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith('Download failed')
    })
  })

  it('retries failed requests', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))
    
    const user = userEvent.setup()
    render(<JobHistory />)
    
    await waitFor(() => {
      expect(screen.getByText('Try Again')).toBeInTheDocument()
    })
    
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockApiResponse)
    })
    
    const retryButton = screen.getByText('Try Again')
    await user.click(retryButton)
    
    await waitFor(() => {
      expect(screen.getByText('products.csv')).toBeInTheDocument()
    })
  })
})