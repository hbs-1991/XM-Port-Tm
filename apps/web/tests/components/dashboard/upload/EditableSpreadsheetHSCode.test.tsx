/**
 * Tests for EditableSpreadsheet component with HS Code functionality
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditableSpreadsheet } from '@/components/dashboard/upload/EditableSpreadsheet';
import { type ProductWithHSCode } from '@shared/types/processing';

// Mock the tooltip component
jest.mock('@/components/shared/ui/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipTrigger: ({ children, asChild }: { children: React.ReactNode, asChild?: boolean }) => 
    asChild ? children : <div>{children}</div>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div role="tooltip">{children}</div>,
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  ChevronLeft: () => <div data-testid="chevron-left">ChevronLeft</div>,
  ChevronRight: () => <div data-testid="chevron-right">ChevronRight</div>,
  Edit2: () => <div data-testid="edit2">Edit2</div>,
  Save: () => <div data-testid="save">Save</div>,
  X: () => <div data-testid="x">X</div>,
  AlertTriangle: () => <div data-testid="alert-triangle">AlertTriangle</div>,
  CheckCircle2: () => <div data-testid="check-circle2">CheckCircle2</div>,
  FileSpreadsheet: () => <div data-testid="file-spreadsheet">FileSpreadsheet</div>,
  Plus: () => <div data-testid="plus">Plus</div>,
  Minus: () => <div data-testid="minus">Minus</div>,
  RotateCcw: () => <div data-testid="rotate-ccw">RotateCcw</div>,
  Download: () => <div data-testid="download">Download</div>,
  Info: () => <div data-testid="info">Info</div>,
  Check: () => <div data-testid="check">Check</div>,
  AlertCircle: () => <div data-testid="alert-circle">AlertCircle</div>,
}));

describe('EditableSpreadsheet with HS Codes', () => {
  const mockData = [
    {
      'Product Description': 'Cotton T-shirt',
      'Quantity': 10,
      'Unit': 'pieces',
      'Value': 100,
      'Origin Country': 'VNM',
      'Unit Price': 10
    },
    {
      'Product Description': 'Wool sweater',
      'Quantity': 5,
      'Unit': 'pieces',
      'Value': 250,
      'Origin Country': 'ITA',
      'Unit Price': 50
    }
  ];

  const mockProductsWithHS: ProductWithHSCode[] = [
    {
      id: '1',
      product_description: 'Cotton T-shirt',
      quantity: 10,
      unit: 'pieces',
      value: 100,
      origin_country: 'VNM',
      unit_price: 10,
      hs_code: '6109.10.00',
      confidence_score: 0.95,
      confidence_level: 'High',
      alternative_hs_codes: ['6109.90.00', '6110.10.00'],
      requires_manual_review: false,
      user_confirmed: true,
      vector_store_reasoning: 'High confidence match for cotton textiles'
    },
    {
      id: '2',
      product_description: 'Wool sweater',
      quantity: 5,
      unit: 'pieces',
      value: 250,
      origin_country: 'ITA',
      unit_price: 50,
      hs_code: '6110.20.00',
      confidence_score: 0.75,
      confidence_level: 'Low',
      alternative_hs_codes: ['6110.10.00'],
      requires_manual_review: true,
      user_confirmed: false,
      vector_store_reasoning: 'Medium confidence match for wool garments'
    }
  ];

  const defaultProps = {
    data: mockData,
    fileName: 'test-file.csv',
    jobId: 'test-job-id',
    hasHSCodes: true,
    productsWithHS: mockProductsWithHS,
    onHSCodeUpdate: jest.fn(),
    onDataChange: jest.fn(),
    onSave: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders HS Code column when hasHSCodes is true', () => {
    render(<EditableSpreadsheet {...defaultProps} />);

    // Check that HS Code column header is present
    expect(screen.getByText('HS Code')).toBeInTheDocument();

    // Check that HS codes are displayed
    expect(screen.getByText('6109.10.00')).toBeInTheDocument();
    expect(screen.getByText('6110.20.00')).toBeInTheDocument();
  });

  it('displays confidence badges correctly', () => {
    render(<EditableSpreadsheet {...defaultProps} />);

    // Check for confidence level badges
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();

    // Check for confidence icons (using data-testid from mocked components)
    expect(screen.getByTestId('check')).toBeInTheDocument(); // High confidence
    expect(screen.getByTestId('alert-triangle')).toBeInTheDocument(); // Low confidence
  });

  it('shows alternative HS codes in tooltip', () => {
    render(<EditableSpreadsheet {...defaultProps} />);

    // Find alternative codes indicators
    const alternativeIndicators = screen.getAllByText(/alternatives/);
    expect(alternativeIndicators).toHaveLength(2);

    // First product should show "2 alternatives"
    expect(screen.getByText('2 alternatives')).toBeInTheDocument();
    // Second product should show "1 alternatives"
    expect(screen.getByText('1 alternatives')).toBeInTheDocument();
  });

  it('shows manual review badge when required', () => {
    render(<EditableSpreadsheet {...defaultProps} />);

    // Should show "Review Required" badge for the second product
    expect(screen.getByText('Review Required')).toBeInTheDocument();
  });

  it('allows editing HS codes', async () => {
    const user = userEvent.setup();
    const mockOnHSCodeUpdate = jest.fn().mockResolvedValue(undefined);

    render(
      <EditableSpreadsheet
        {...defaultProps}
        onHSCodeUpdate={mockOnHSCodeUpdate}
        readOnly={false}
      />
    );

    // Find and click the edit button for the first HS code
    const editButtons = screen.getAllByTestId('edit2');
    await user.click(editButtons[0]);

    // Should show input field with current HS code
    const input = screen.getByDisplayValue('6109.10.00');
    expect(input).toBeInTheDocument();

    // Change the HS code
    await user.clear(input);
    await user.type(input, '6109.90.00');

    // Click save
    const saveButton = screen.getByTestId('save');
    await user.click(saveButton);

    // Verify onHSCodeUpdate was called with correct parameters
    await waitFor(() => {
      expect(mockOnHSCodeUpdate).toHaveBeenCalledWith('1', '6109.90.00');
    });
  });

  it('validates HS code format during editing', async () => {
    const user = userEvent.setup();
    const mockOnHSCodeUpdate = jest.fn().mockResolvedValue(undefined);

    render(
      <EditableSpreadsheet
        {...defaultProps}
        onHSCodeUpdate={mockOnHSCodeUpdate}
        readOnly={false}
      />
    );

    // Find and click the edit button
    const editButtons = screen.getAllByTestId('edit2');
    await user.click(editButtons[0]);

    // Try to enter an invalid HS code
    const input = screen.getByDisplayValue('6109.10.00');
    await user.clear(input);
    await user.type(input, 'invalid');

    // Click save
    const saveButton = screen.getByTestId('save');
    await user.click(saveButton);

    // Verify onHSCodeUpdate was NOT called due to validation failure
    expect(mockOnHSCodeUpdate).not.toHaveBeenCalled();
  });

  it('cancels HS code editing when escape is pressed', async () => {
    const user = userEvent.setup();

    render(<EditableSpreadsheet {...defaultProps} readOnly={false} />);

    // Start editing
    const editButtons = screen.getAllByTestId('edit2');
    await user.click(editButtons[0]);

    // Verify input is visible
    const input = screen.getByDisplayValue('6109.10.00');
    expect(input).toBeInTheDocument();

    // Press escape
    fireEvent.keyDown(input, { key: 'Escape' });

    // Input should be gone
    expect(screen.queryByDisplayValue('6109.10.00')).not.toBeInTheDocument();
    // Original HS code should still be visible as text
    expect(screen.getByText('6109.10.00')).toBeInTheDocument();
  });

  it('exports CSV with HS codes when enabled', () => {
    // Mock URL.createObjectURL and document.createElement
    const mockCreateObjectURL = jest.fn().mockReturnValue('blob:url');
    const mockClick = jest.fn();
    const mockLink = {
      href: '',
      download: '',
      click: mockClick
    };

    global.URL.createObjectURL = mockCreateObjectURL;
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);

    render(<EditableSpreadsheet {...defaultProps} />);

    // Click export button
    const exportButton = screen.getByText('Export CSV');
    fireEvent.click(exportButton);

    // Verify that the download filename includes 'with_hs_codes'
    expect(mockLink.download).toContain('with_hs_codes_');
    expect(mockClick).toHaveBeenCalled();

    // Clean up mocks
    jest.restoreAllMocks();
  });

  it('handles missing HS code data gracefully', () => {
    // Render without HS code data
    render(
      <EditableSpreadsheet
        {...defaultProps}
        hasHSCodes={false}
        productsWithHS={undefined}
      />
    );

    // Should not show HS Code column
    expect(screen.queryByText('HS Code')).not.toBeInTheDocument();
    
    // Should still show regular columns
    expect(screen.getByText('Product Description')).toBeInTheDocument();
    expect(screen.getByText('Quantity')).toBeInTheDocument();
  });

  it('is read-only when readOnly prop is true', () => {
    render(<EditableSpreadsheet {...defaultProps} readOnly={true} />);

    // Should not show edit buttons
    expect(screen.queryByTestId('edit2')).not.toBeInTheDocument();
    
    // Should still display HS codes
    expect(screen.getByText('6109.10.00')).toBeInTheDocument();
    expect(screen.getByText('6110.20.00')).toBeInTheDocument();
  });

  it('shows loading state during HS code update', async () => {
    const user = userEvent.setup();
    const mockOnHSCodeUpdate = jest.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );

    render(
      <EditableSpreadsheet
        {...defaultProps}
        onHSCodeUpdate={mockOnHSCodeUpdate}
        readOnly={false}
      />
    );

    // Start editing
    const editButtons = screen.getAllByTestId('edit2');
    await user.click(editButtons[0]);

    // Enter new HS code
    const input = screen.getByDisplayValue('6109.10.00');
    await user.clear(input);
    await user.type(input, '6109.90.00');

    // Click save
    const saveButton = screen.getByTestId('save');
    await user.click(saveButton);

    // Save button should be disabled during update
    expect(saveButton).toBeDisabled();
  });

  it('handles pagination correctly with HS codes', () => {
    // Create more data to test pagination
    const moreData = Array.from({ length: 25 }, (_, i) => ({
      'Product Description': `Product ${i + 1}`,
      'Quantity': 1,
      'Unit': 'piece',
      'Value': 10,
      'Origin Country': 'USA',
      'Unit Price': 10
    }));

    const moreProductsWithHS: ProductWithHSCode[] = Array.from({ length: 25 }, (_, i) => ({
      id: String(i + 1),
      product_description: `Product ${i + 1}`,
      quantity: 1,
      unit: 'piece',
      value: 10,
      origin_country: 'USA',
      unit_price: 10,
      hs_code: '6109.10.00',
      confidence_score: 0.9,
      confidence_level: 'High',
      alternative_hs_codes: [],
      requires_manual_review: false,
      user_confirmed: true
    }));

    render(
      <EditableSpreadsheet
        {...defaultProps}
        data={moreData}
        productsWithHS={moreProductsWithHS}
      />
    );

    // Should show pagination controls
    expect(screen.getByText('Previous')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();

    // Should show row count
    expect(screen.getByText(/Showing \d+ to \d+ of 25 rows/)).toBeInTheDocument();

    // First page should show first 20 items
    expect(screen.getByText('Product 1')).toBeInTheDocument();
    expect(screen.queryByText('Product 25')).not.toBeInTheDocument();
  });
});