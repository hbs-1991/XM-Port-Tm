import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { JobDetails } from '@/components/dashboard/JobDetails';
import { JobDetailsResponse, ProcessingStatus } from '@shared/types/processing';

// Mock fetch
global.fetch = jest.fn();

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  CheckCircle: () => <div data-testid="check-circle-icon">✓</div>,
  XCircle: () => <div data-testid="x-circle-icon">✗</div>,
  AlertTriangle: () => <div data-testid="alert-triangle-icon">⚠</div>,
  Clock: () => <div data-testid="clock-icon">⏰</div>,
  FileText: () => <div data-testid="file-text-icon">📄</div>,
  BarChart3: () => <div data-testid="bar-chart-icon">📊</div>,
  Download: () => <div data-testid="download-icon">⬇</div>,
  Edit3: () => <div data-testid="edit-icon">✏</div>,
  Save: () => <div data-testid="save-icon">💾</div>,
  X: () => <div data-testid="x-icon">✕</div>,
  Loader2: () => <div data-testid="loader-icon">🔄</div>,
  Eye: () => <div data-testid="eye-icon">👁</div>,
}));

const mockJobDetailsResponse: JobDetailsResponse = {
  job: {
    id: 'job-123',
    status: ProcessingStatus.COMPLETED,
    input_file_name: 'test-products.xlsx',
    country_schema: 'USA',
    input_file_size: 12345,
    credits_used: 5,
    processing_time_ms: 15000,
    total_products: 10,
    successful_matches: 8,
    average_confidence: 0.85,
    has_xml_output: true,
    xml_generation_status: 'COMPLETED',
    error_message: null,
    created_at: '2024-01-15T10:00:00Z',
    started_at: '2024-01-15T10:00:30Z',
    completed_at: '2024-01-15T10:00:45Z'
  },
  product_matches: [
    {
      id: 'match-1',
      product_description: 'Wireless Bluetooth Headphones',
      quantity: 100,
      unit_of_measure: 'pcs',
      value: 2500.00,
      origin_country: 'CHN',
      matched_hs_code: '8518.30.20',
      confidence_score: 0.92,
      alternative_hs_codes: ['8518.30.10', '8518.40.00'],
      vector_store_reasoning: 'Matched based on electronics category and audio equipment specifications',
      requires_manual_review: false,
      user_confirmed: true,
      created_at: '2024-01-15T10:00:35Z'
    },
    {
      id: 'match-2',
      product_description: 'Organic Cotton T-Shirt',
      quantity: 50,
      unit_of_measure: 'pcs',
      value: 750.00,
      origin_country: 'IND',
      matched_hs_code: '6109.10.00',
      confidence_score: 0.65,
      alternative_hs_codes: ['6109.90.10', '6110.20.20'],
      vector_store_reasoning: 'Low confidence match - requires review',
      requires_manual_review: true,
      user_confirmed: false,
      created_at: '2024-01-15T10:00:40Z'
    }
  ],
  statistics: {
    total_matches: 2,
    high_confidence_matches: 1,
    manual_review_required: 1,
    user_confirmed: 1,
    success_rate: 80.0
  }
};

const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

beforeEach(() => {
  mockFetch.mockClear();
});

describe('JobDetails Component', () => {
  const defaultProps = {
    jobId: 'job-123',
    isOpen: true,
    onClose: jest.fn()
  };

  it('renders loading state correctly', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<JobDetails {...defaultProps} />);
    
    expect(screen.getByText('Loading job details...')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
  });

  it('renders error state correctly', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it('renders job details successfully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('test-products.xlsx')).toBeInTheDocument();
      expect(screen.getByText('USA')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // Credits
      expect(screen.getByText('15s')).toBeInTheDocument(); // Processing time
    });
  });

  it('displays product matches correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Wireless Bluetooth Headphones')).toBeInTheDocument();
      expect(screen.getByText('Organic Cotton T-Shirt')).toBeInTheDocument();
      expect(screen.getByText('8518.30.20')).toBeInTheDocument();
      expect(screen.getByText('6109.10.00')).toBeInTheDocument();
      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText('65%')).toBeInTheDocument();
    });
  });

  it('shows statistics correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // Total matches
      expect(screen.getByText('1')).toBeInTheDocument(); // High confidence
      expect(screen.getByText('1')).toBeInTheDocument(); // Manual review
      expect(screen.getByText('80%')).toBeInTheDocument(); // Success rate
    });
  });

  it('displays confidence scores with correct colors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const highConfidence = screen.getByText('92%');
      const lowConfidence = screen.getByText('65%');
      
      expect(highConfidence).toHaveClass('text-green-600');
      expect(lowConfidence).toHaveClass('text-yellow-600');
    });
  });

  it('shows badges for review and confirmation status', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Review')).toBeInTheDocument();
      expect(screen.getByText('Confirmed')).toBeInTheDocument();
    });
  });

  it('enables edit mode when Edit Data button is clicked', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const editButton = screen.getByText('Edit Data');
      fireEvent.click(editButton);
      
      expect(screen.getByText('Save Changes')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
      expect(screen.getByDisplayValue('8518.30.20')).toBeInTheDocument(); // HS Code input
    });
  });

  it('allows editing HS codes in edit mode', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const editButton = screen.getByText('Edit Data');
      fireEvent.click(editButton);
      
      const hsCodeInput = screen.getByDisplayValue('8518.30.20');
      fireEvent.change(hsCodeInput, { target: { value: '8518.30.30' } });
      
      expect(screen.getByDisplayValue('8518.30.30')).toBeInTheDocument();
      expect(screen.getByText('Save Changes')).not.toBeDisabled();
    });
  });

  it('toggles user confirmation status in edit mode', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const editButton = screen.getByText('Edit Data');
      fireEvent.click(editButton);
      
      const confirmButtons = screen.getAllByText('Confirm');
      fireEvent.click(confirmButtons[0]); // Click the first confirm button
      
      expect(screen.getByText('Save Changes')).not.toBeDisabled();
    });
  });

  it('cancels edit mode without saving changes', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const editButton = screen.getByText('Edit Data');
      fireEvent.click(editButton);
      
      const hsCodeInput = screen.getByDisplayValue('8518.30.20');
      fireEvent.change(hsCodeInput, { target: { value: '8518.30.30' } });
      
      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);
      
      expect(screen.getByText('Edit Data')).toBeInTheDocument();
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
    });
  });

  it('saves changes successfully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const editButton = screen.getByText('Edit Data');
      fireEvent.click(editButton);
      
      const hsCodeInput = screen.getByDisplayValue('8518.30.20');
      fireEvent.change(hsCodeInput, { target: { value: '8518.30.30' } });
      
      const saveButton = screen.getByText('Save Changes');
      fireEvent.click(saveButton);
      
      expect(screen.getByText('Edit Data')).toBeInTheDocument();
    });
  });

  it('shows alternative HS codes dropdown in edit mode', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const editButton = screen.getByText('Edit Data');
      fireEvent.click(editButton);
      
      expect(screen.getByText('Current: 8518.30.20')).toBeInTheDocument();
      expect(screen.getByText('Alt: 8518.30.10')).toBeInTheDocument();
      expect(screen.getByText('Alt: 8518.40.00')).toBeInTheDocument();
    });
  });

  it('filters high confidence matches correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const highConfidenceTab = screen.getByText(/High Confidence/);
      fireEvent.click(highConfidenceTab);
      
      expect(screen.getByText('Wireless Bluetooth Headphones')).toBeInTheDocument();
      expect(screen.queryByText('Organic Cotton T-Shirt')).not.toBeInTheDocument();
    });
  });

  it('filters items requiring review correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobDetailsResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      const reviewTab = screen.getByText(/Need Review/);
      fireEvent.click(reviewTab);
      
      expect(screen.queryByText('Wireless Bluetooth Headphones')).not.toBeInTheDocument();
      expect(screen.getByText('Organic Cotton T-Shirt')).toBeInTheDocument();
    });
  });

  it('closes modal when onClose is called', () => {
    const mockOnClose = jest.fn();
    
    render(<JobDetails {...defaultProps} isOpen={false} onClose={mockOnClose} />);
    
    expect(screen.queryByText('Job Details')).not.toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Job not found' })
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch job details: 404/)).toBeInTheDocument();
    });
  });

  it('formats file sizes correctly', async () => {
    const largeFileResponse = {
      ...mockJobDetailsResponse,
      job: {
        ...mockJobDetailsResponse.job,
        input_file_size: 1048576 // 1MB
      }
    };
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => largeFileResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('1 MB')).toBeInTheDocument();
    });
  });

  it('formats processing time correctly', async () => {
    const longProcessingResponse = {
      ...mockJobDetailsResponse,
      job: {
        ...mockJobDetailsResponse.job,
        processing_time_ms: 125000 // 2m 5s
      }
    };
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => longProcessingResponse
    } as Response);
    
    render(<JobDetails {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('2m 5s')).toBeInTheDocument();
    });
  });
});