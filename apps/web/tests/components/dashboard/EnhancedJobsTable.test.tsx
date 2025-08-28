/**
 * EnhancedJobsTable component tests
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EnhancedJobsTable, EnhancedJobsTableSkeleton, type JobData } from '@/components/dashboard/EnhancedJobsTable';

// Mock the hooks
jest.mock('@/hooks/useDebounce', () => ({
  useDebounce: (value: any) => value // Return the value immediately for testing
}));

const mockConnectionStatus = {
  connected: true,
  reconnecting: false,
  error: null
};

jest.mock('@/hooks/useJobUpdates', () => ({
  useJobUpdates: () => ({
    connectionStatus: mockConnectionStatus,
    lastUpdate: null,
    updatedJobIds: new Set(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    clearUpdatedJobs: jest.fn()
  })
}));

const mockJobs: JobData[] = [
  {
    id: '1',
    fileName: 'import_batch_2024_01.xlsx',
    status: 'completed',
    dateCreated: '2024-01-23T14:30:00Z',
    dateCompleted: '2024-01-23T14:45:00Z',
    productsCount: 150,
    confidenceScore: 96.5,
    fileSize: 2048576,
    fileType: 'xlsx',
    downloadUrl: '/api/jobs/1/download'
  },
  {
    id: '2',
    fileName: 'export_products_jan.csv',
    status: 'processing',
    dateCreated: '2024-01-23T13:45:00Z',
    productsCount: 87,
    fileSize: 1024000,
    fileType: 'csv'
  },
  {
    id: '3',
    fileName: 'customs_declaration.xlsx',
    status: 'failed',
    dateCreated: '2024-01-23T12:20:00Z',
    productsCount: 234,
    fileSize: 3145728,
    fileType: 'xlsx',
    errorMessage: 'Invalid file format'
  },
  {
    id: '4',
    fileName: 'pending_job.csv',
    status: 'pending',
    dateCreated: '2024-01-23T11:15:00Z',
    productsCount: 45,
    fileSize: 512000,
    fileType: 'csv'
  }
];

// Mock window.innerWidth for responsive testing
const mockWindowSize = (width: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });

  // Trigger resize event
  window.dispatchEvent(new Event('resize'));
};

describe('EnhancedJobsTable', () => {
  const mockOnJobAction = jest.fn();
  const mockOnJobDetails = jest.fn();
  const mockOnRefresh = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockWindowSize(1024); // Desktop size by default
  });

  it('renders jobs table with correct data', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Check header
    expect(screen.getByText('Processing Jobs')).toBeInTheDocument();
    expect(screen.getByText('4 jobs found')).toBeInTheDocument();
    
    // Check connection status
    expect(screen.getByText('Live')).toBeInTheDocument();
    
    // Check if jobs are displayed
    expect(screen.getByText('import_batch_2024_01.xlsx')).toBeInTheDocument();
    expect(screen.getByText('export_products_jan.csv')).toBeInTheDocument();
    expect(screen.getByText('customs_declaration.xlsx')).toBeInTheDocument();
    expect(screen.getByText('pending_job.csv')).toBeInTheDocument();
  });

  it('shows skeleton when loading', () => {
    render(<EnhancedJobsTable loading={true} jobs={[]} />);
    
    // Should render skeleton loader
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('handles search functionality', async () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    const searchInput = screen.getByPlaceholderText('Search jobs...');
    fireEvent.change(searchInput, { target: { value: 'import' } });
    
    await waitFor(() => {
      // Should show filtered results
      expect(screen.getByText('import_batch_2024_01.xlsx')).toBeInTheDocument();
      expect(screen.queryByText('export_products_jan.csv')).not.toBeInTheDocument();
    });
  });

  it('handles status filtering', async () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Open status filter
    const statusSelect = screen.getByDisplayValue('Status');
    fireEvent.click(statusSelect);
    
    // Select completed status
    const completedOption = screen.getByText('Completed');
    fireEvent.click(completedOption);
    
    await waitFor(() => {
      // Should show only completed jobs
      expect(screen.getByText('import_batch_2024_01.xlsx')).toBeInTheDocument();
      expect(screen.queryByText('export_products_jan.csv')).not.toBeInTheDocument();
    });
  });

  it('handles job selection and bulk actions', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Select first job
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]); // First job checkbox (0 is select all)
    
    // Should show bulk actions
    expect(screen.getByText('1 job selected')).toBeInTheDocument();
    
    // Click bulk download
    const downloadButton = screen.getByText('Download');
    fireEvent.click(downloadButton);
    
    expect(mockOnJobAction).toHaveBeenCalledWith('download', ['1']);
  });

  it('handles individual job actions', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Click on more options for first job
    const moreButtons = screen.getAllByRole('button', { name: /More/ });
    fireEvent.click(moreButtons[0]);
    
    // Click view details
    const viewDetailsButton = screen.getByText('View Details');
    fireEvent.click(viewDetailsButton);
    
    expect(mockOnJobDetails).toHaveBeenCalledWith('1');
  });

  it('handles pagination', () => {
    const manyJobs = Array.from({ length: 25 }, (_, i) => ({
      ...mockJobs[0],
      id: i.toString(),
      fileName: `job_${i}.xlsx`
    }));

    render(
      <EnhancedJobsTable 
        jobs={manyJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Should show pagination
    expect(screen.getByText(/Page 1 of/)).toBeInTheDocument();
    
    // Should show items per page selector
    expect(screen.getByText('Rows per page:')).toBeInTheDocument();
    
    // Click next page
    const nextButton = screen.getByRole('button', { name: /Next/ });
    fireEvent.click(nextButton);
    
    // Should be on page 2
    expect(screen.getByText(/Page 2 of/)).toBeInTheDocument();
  });

  it('displays different status icons and badges correctly', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Check status badges
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Processing')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('switches to mobile card view on smaller screens', () => {
    // Set mobile viewport
    mockWindowSize(600);
    
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Should render cards instead of table
    // The table headers should not be visible in mobile view
    expect(screen.queryByText('File Name')).not.toBeInTheDocument();
    
    // But job data should still be visible in card format
    expect(screen.getByText('import_batch_2024_01.xlsx')).toBeInTheDocument();
  });

  it('handles sorting functionality', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Open sort dropdown
    const sortSelect = screen.getByDisplayValue(/Newest/);
    fireEvent.click(sortSelect);
    
    // Select name sorting
    const nameSort = screen.getByText('Name A-Z');
    fireEvent.click(nameSort);
    
    // Jobs should be reordered (testing this would require checking DOM order)
    expect(screen.getByDisplayValue(/Name A-Z/)).toBeInTheDocument();
  });

  it('shows error messages for failed jobs', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Switch to mobile view to see error message in cards
    mockWindowSize(600);
    
    // Re-render with mobile view
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Should show error message for failed job
    expect(screen.getByText('Invalid file format')).toBeInTheDocument();
  });

  it('includes proper accessibility attributes', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    // Check for ARIA labels
    const tableRegion = screen.getByRole('region');
    expect(tableRegion).toHaveAttribute('aria-label', 'Jobs table');
    
    // Check for table accessibility
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
    
    // Check checkbox accessibility
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).toHaveAttribute('aria-label', 'Select all jobs');
  });

  it('handles refresh functionality', () => {
    render(
      <EnhancedJobsTable 
        jobs={mockJobs}
        onJobAction={mockOnJobAction}
        onJobDetails={mockOnJobDetails}
        onRefresh={mockOnRefresh}
      />
    );
    
    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);
    
    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });
});

describe('EnhancedJobsTableSkeleton', () => {
  it('renders skeleton loading state', () => {
    render(<EnhancedJobsTableSkeleton />);
    
    // Should render skeleton elements
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
    
    // Check accessibility
    const statusElement = screen.getByRole('status');
    expect(statusElement).toHaveAttribute('aria-label', 'Loading jobs table');
  });

  it('applies custom className', () => {
    render(<EnhancedJobsTableSkeleton className="custom-class" />);
    
    const container = screen.getByRole('status');
    expect(container).toHaveClass('custom-class');
  });

  it('renders all skeleton sections', () => {
    render(<EnhancedJobsTableSkeleton />);
    
    // Should render header, filters, table, and pagination skeletons
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(10); // Multiple skeleton elements
  });
});