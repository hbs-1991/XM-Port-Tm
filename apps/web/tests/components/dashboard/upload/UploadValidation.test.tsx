import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UploadValidation } from '@/components/dashboard/upload/UploadValidation';
import * as processingService from '@/services/processing';

// Mock the processing service
jest.mock('@/services/processing');
const mockValidateFile = processingService.validateFile as jest.MockedFunction<typeof processingService.validateFile>;

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  CheckCircle2: () => <div data-testid="check-circle-icon" />,
  AlertCircle: () => <div data-testid="alert-circle-icon" />,
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  FileText: () => <div data-testid="file-text-icon" />,
  BarChart3: () => <div data-testid="bar-chart-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />
}));

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Mock file for testing
const createMockFile = (name: string, type: string): File => {
  const file = new File(['test content'], name, { type });
  return file;
};

describe('UploadValidation Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders validation component with file text icon', () => {
    const mockFile = createMockFile('test.csv', 'text/csv');

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    expect(screen.getByTestId('file-text-icon')).toBeInTheDocument();
    expect(screen.getByText('Real-time Validation')).toBeInTheDocument();
  });

  it('shows loading state during validation', () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    mockValidateFile.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    expect(screen.getByText('Validating file...')).toBeInTheDocument();
    expect(screen.getByTestId('clock-icon')).toBeInTheDocument();
  });

  it('displays successful validation results', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockResult = {
      valid: true,
      errors: [],
      warnings: [],
      total_rows: 100,
      valid_rows: 100,
      summary: {
        total_errors: 0,
        total_warnings: 0,
        errors_by_field: {},
        errors_by_type: {},
        most_common_errors: [],
        data_quality_score: 95
      }
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('File validation successful! 100 of 100 rows are valid.')).toBeInTheDocument();
    });

    expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
    expect(screen.getByText('100 Total Rows')).toBeInTheDocument();
    expect(screen.getByText('100 Valid Rows')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('Excellent')).toBeInTheDocument();
  });

  it('displays validation errors', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockResult = {
      valid: false,
      errors: [
        {
          field: 'quantity',
          error: 'Invalid quantity value',
          row: 5
        },
        {
          field: 'price',
          error: 'Price must be positive',
          row: 10
        }
      ],
      warnings: ['Column name mismatch'],
      total_rows: 50,
      valid_rows: 48,
      summary: {
        total_errors: 2,
        total_warnings: 1,
        errors_by_field: { quantity: 1, price: 1 },
        errors_by_type: { 'invalid_value': 2 },
        most_common_errors: ['Invalid quantity value', 'Price must be positive'],
        data_quality_score: 70
      }
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Validation failed with 2 error(s).')).toBeInTheDocument();
    });

    expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument();
    expect(screen.getByText('2 Errors')).toBeInTheDocument();
    expect(screen.getByText('1 Warning')).toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();

    // Check error details
    expect(screen.getByText('quantity:')).toBeInTheDocument();
    expect(screen.getByText('Invalid quantity value')).toBeInTheDocument();
    expect(screen.getByText('(Row 5)')).toBeInTheDocument();
  });

  it('shows warnings when present', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockResult = {
      valid: true,
      errors: [],
      warnings: ['Encoding might cause issues', 'Column names are similar to requirements'],
      total_rows: 25,
      valid_rows: 25,
      summary: {
        total_errors: 0,
        total_warnings: 2,
        errors_by_field: {},
        errors_by_type: {},
        most_common_errors: [],
        data_quality_score: 85
      }
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('2 Warnings')).toBeInTheDocument();
    });

    expect(screen.getByText('Warnings')).toBeInTheDocument();
    expect(screen.getByText('Encoding might cause issues')).toBeInTheDocument();
    expect(screen.getByText('Column names are similar to requirements')).toBeInTheDocument();
  });

  it('handles validation service errors', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    mockValidateFile.mockRejectedValue(new Error('Network error'));

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Validation failed with 1 error(s).')).toBeInTheDocument();
    });

    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('calls onValidationComplete with results', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockOnValidationComplete = jest.fn();
    const mockResult = {
      valid: true,
      errors: [],
      warnings: [],
      total_rows: 10,
      valid_rows: 10
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} onValidationComplete={mockOnValidationComplete} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnValidationComplete).toHaveBeenCalledWith(mockResult);
    });
  });

  it('allows retry functionality', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockOnRetry = jest.fn();
    const mockResult = {
      valid: false,
      errors: [{ field: 'test', error: 'Test error' }],
      warnings: [],
      total_rows: 5,
      valid_rows: 4
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} onRetry={mockOnRetry} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    const retryButton = screen.getByText('Retry');
    await userEvent.click(retryButton);

    expect(mockOnRetry).toHaveBeenCalled();
    expect(mockValidateFile).toHaveBeenCalledTimes(2); // Initial call + retry
  });

  it('expands error details on request', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockResult = {
      valid: false,
      errors: [
        { field: 'field1', error: 'Error 1' },
        { field: 'field2', error: 'Error 2' },
        { field: 'field3', error: 'Error 3' },
        { field: 'field4', error: 'Error 4' },
        { field: 'field5', error: 'Error 5' }
      ],
      warnings: [],
      total_rows: 10,
      valid_rows: 5
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Show 2 More Errors')).toBeInTheDocument();
    });

    const showMoreButton = screen.getByText('Show 2 More Errors');
    await userEvent.click(showMoreButton);

    expect(screen.getByText('Error 4')).toBeInTheDocument();
    expect(screen.getByText('Error 5')).toBeInTheDocument();
    expect(screen.getByText('Show Less')).toBeInTheDocument();
  });

  it('displays most common errors summary', async () => {
    const mockFile = createMockFile('test.csv', 'text/csv');
    const mockResult = {
      valid: false,
      errors: [{ field: 'test', error: 'Test error' }],
      warnings: [],
      total_rows: 10,
      valid_rows: 9,
      summary: {
        total_errors: 1,
        total_warnings: 0,
        errors_by_field: { test: 1 },
        errors_by_type: { validation: 1 },
        most_common_errors: ['Invalid data format', 'Missing required fields'],
        data_quality_score: 60
      }
    };

    mockValidateFile.mockResolvedValue(mockResult);

    render(
      <TestWrapper>
        <UploadValidation file={mockFile} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Most Common Issues')).toBeInTheDocument();
    });

    expect(screen.getByText('• Invalid data format')).toBeInTheDocument();
    expect(screen.getByText('• Missing required fields')).toBeInTheDocument();
  });

  it('re-validates when file changes', async () => {
    const mockFile1 = createMockFile('test1.csv', 'text/csv');
    const mockFile2 = createMockFile('test2.csv', 'text/csv');

    mockValidateFile.mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
      total_rows: 10,
      valid_rows: 10
    });

    const { rerender } = render(
      <TestWrapper>
        <UploadValidation file={mockFile1} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockValidateFile).toHaveBeenCalledTimes(1);
    });

    rerender(
      <TestWrapper>
        <UploadValidation file={mockFile2} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockValidateFile).toHaveBeenCalledTimes(2);
    });

    expect(mockValidateFile).toHaveBeenLastCalledWith(mockFile2);
  });
});