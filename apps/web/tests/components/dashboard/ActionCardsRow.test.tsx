/**
 * ActionCardsRow component tests
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ActionCardsRow, ActionCardsRowSkeleton, type ActionCardsData } from '@/components/dashboard/ActionCardsRow';

const mockActionCardsData: ActionCardsData = {
  upload: {
    allowedTypes: ['.xlsx', '.xls', '.csv'],
    maxSize: 25 * 1024 * 1024, // 25MB
    isUploading: false
  },
  monthlyOverview: {
    currentMonth: {
      creditsUsed: 450,
      jobsCompleted: 28,
      avgProcessingTime: 4200
    },
    previousMonth: {
      creditsUsed: 380,
      jobsCompleted: 24,
      avgProcessingTime: 4800
    },
    chartData: [
      { month: 'Jun', jobs: 18, credits: 380 },
      { month: 'Jul', jobs: 24, credits: 420 },
      { month: 'Aug', jobs: 28, credits: 450 }
    ]
  },
  performance: {
    successRate: 98.5,
    totalJobs: 127,
    successfulJobs: 124,
    failedJobs: 2,
    pendingJobs: 1
  }
};

// Mock recharts components
jest.mock('recharts', () => ({
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
  Legend: () => <div data-testid="legend" />
}));

// Mock react-dropzone
const mockDropzone = {
  getRootProps: () => ({
    'data-testid': 'dropzone-root'
  }),
  getInputProps: () => ({
    'data-testid': 'dropzone-input'
  }),
  isDragActive: false,
  fileRejections: []
};

jest.mock('react-dropzone', () => ({
  useDropzone: () => mockDropzone
}));

describe('ActionCardsRow', () => {
  const mockOnFileUpload = jest.fn();
  const mockOnRetry = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all three action cards with correct data', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
        onRetry={mockOnRetry}
      />
    );
    
    // Check if all cards are rendered
    expect(screen.getByText('Quick Upload')).toBeInTheDocument();
    expect(screen.getByText('Monthly Overview')).toBeInTheDocument();
    expect(screen.getByText('Processing Performance')).toBeInTheDocument();
    
    // Check specific data
    expect(screen.getByText('450')).toBeInTheDocument(); // Credits used
    expect(screen.getByText('28')).toBeInTheDocument(); // Jobs completed
    expect(screen.getByText('98.5%')).toBeInTheDocument(); // Success rate
  });

  it('shows skeleton when loading', () => {
    render(<ActionCardsRow loading={true} />);
    
    // Should render skeleton loader
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('shows skeleton when no data provided', () => {
    render(<ActionCardsRow />);
    
    // Should render skeleton loader when no data
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('renders charts correctly', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Check that chart components are rendered
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    expect(screen.getAllByTestId('responsive-container')).toHaveLength(2);
  });

  it('handles file upload interactions', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Check upload elements are present
    expect(screen.getByTestId('dropzone-root')).toBeInTheDocument();
    expect(screen.getByTestId('dropzone-input')).toBeInTheDocument();
    expect(screen.getByText('Browse Files')).toBeInTheDocument();
  });

  it('displays upload restrictions correctly', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Check file type restrictions
    expect(screen.getByText(/Supported: .xlsx, .xls, .csv/)).toBeInTheDocument();
    expect(screen.getByText(/Max size: 25MB per file/)).toBeInTheDocument();
  });

  it('shows uploading state correctly', () => {
    const uploadingData = {
      ...mockActionCardsData,
      upload: {
        ...mockActionCardsData.upload,
        isUploading: true
      }
    };

    render(
      <ActionCardsRow 
        data={uploadingData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Check uploading indicators
    expect(screen.getByText(/Uploading files/)).toBeInTheDocument();
    expect(screen.getByText(/Processing files... 65% complete/)).toBeInTheDocument();
  });

  it('calculates trends correctly in monthly overview', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Credits change: 450 - 380 = +70
    expect(screen.getByText('+70 from last month')).toBeInTheDocument();
    
    // Jobs change: 28 - 24 = +4  
    expect(screen.getByText('+4 from last month')).toBeInTheDocument();
    
    // Time improvement should show as positive (lower time is better)
    // avgProcessingTime: 4200s vs 4800s = -600s = -10m improvement
    expect(screen.getByText(/-10m vs last month/)).toBeInTheDocument();
  });

  it('displays performance metrics correctly', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Check performance data
    expect(screen.getByText('98.5%')).toBeInTheDocument(); // Success rate
    expect(screen.getByText('Overall Success Rate')).toBeInTheDocument();
    expect(screen.getByText('127')).toBeInTheDocument(); // Total jobs in center
    expect(screen.getByText('Total')).toBeInTheDocument();
  });

  it('includes proper accessibility attributes', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    // Check for ARIA labels
    const cardsRegion = screen.getByRole('region');
    expect(cardsRegion).toHaveAttribute('aria-label', 'Interactive action cards');
    
    // Check for file upload accessibility
    const uploadInput = screen.getByLabelText('File upload input');
    expect(uploadInput).toBeInTheDocument();
  });

  it('applies responsive grid classes', () => {
    render(
      <ActionCardsRow 
        data={mockActionCardsData}
        onFileUpload={mockOnFileUpload}
      />
    );
    
    const container = screen.getByRole('region');
    expect(container).toHaveClass('grid-cols-1', 'md:grid-cols-2', 'xl:grid-cols-3');
  });
});

describe('ActionCardsRowSkeleton', () => {
  it('renders skeleton loading state', () => {
    render(<ActionCardsRowSkeleton />);
    
    // Should render 3 skeleton cards
    const skeletonCards = document.querySelectorAll('.animate-pulse');
    expect(skeletonCards.length).toBe(3);
    
    // Check accessibility
    const statusElement = screen.getByRole('status');
    expect(statusElement).toHaveAttribute('aria-label', 'Loading action cards');
  });

  it('applies custom className', () => {
    render(<ActionCardsRowSkeleton className="custom-class" />);
    
    const container = screen.getByRole('status');
    expect(container).toHaveClass('custom-class');
  });

  it('has correct responsive grid structure', () => {
    render(<ActionCardsRowSkeleton />);
    
    const container = screen.getByRole('status');
    expect(container).toHaveClass('grid-cols-1', 'md:grid-cols-2', 'xl:grid-cols-3');
  });
});