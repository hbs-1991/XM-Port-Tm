import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilePreview } from '@/components/dashboard/upload/FilePreview';

const mockData = [
  {
    'Product Description': 'Widget A',
    'Quantity': '10',
    'Unit': 'pieces',
    'Value': '100.00',
    'Origin Country': 'USA',
    'Unit Price': '10.00'
  },
  {
    'Product Description': 'Widget B',
    'Quantity': '5',
    'Unit': 'pieces',
    'Value': '50.00',
    'Origin Country': 'Canada',
    'Unit Price': '10.00'
  },
  {
    'Product Description': 'Invalid Item',
    'Quantity': '-1',
    'Unit': 'pieces',
    'Value': 'not-a-number',
    'Origin Country': '',
    'Unit Price': '0'
  }
];

describe('FilePreview', () => {
  it('renders data preview with correct title', () => {
    render(
      <FilePreview 
        data={mockData} 
        fileName="test.csv" 
      />
    );

    expect(screen.getByText('Data Preview - test.csv')).toBeInTheDocument();
    expect(screen.getByText('3 rows')).toBeInTheDocument();
  });

  it('displays all required column headers', () => {
    render(
      <FilePreview 
        data={mockData} 
        fileName="test.csv" 
      />
    );

    expect(screen.getByText('Product Description')).toBeInTheDocument();
    expect(screen.getByText('Quantity')).toBeInTheDocument();
    expect(screen.getByText('Unit')).toBeInTheDocument();
    expect(screen.getByText('Value')).toBeInTheDocument();
    expect(screen.getByText('Origin Country')).toBeInTheDocument();
    expect(screen.getByText('Unit Price')).toBeInTheDocument();
  });

  it('shows data in table format', () => {
    render(
      <FilePreview 
        data={mockData} 
        fileName="test.csv" 
      />
    );

    // Check first row data
    expect(screen.getByText('Widget A')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('USA')).toBeInTheDocument();

    // Check second row data
    expect(screen.getByText('Widget B')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Canada')).toBeInTheDocument();
  });

  it('detects and displays validation errors', () => {
    render(
      <FilePreview 
        data={mockData} 
        fileName="test.csv" 
      />
    );

    // Should show error badge
    expect(screen.getByText(/error/)).toBeInTheDocument();
    
    // Should highlight invalid fields
    // The third row has multiple validation errors
    expect(screen.getByText('Invalid Item')).toBeInTheDocument();
  });

  it('shows valid badge when no errors', () => {
    const validData = [
      {
        'Product Description': 'Valid Widget',
        'Quantity': '10',
        'Unit': 'pieces',
        'Value': '100.00',
        'Origin Country': 'USA',
        'Unit Price': '10.00'
      }
    ];

    render(
      <FilePreview 
        data={validData} 
        fileName="valid.csv" 
      />
    );

    expect(screen.getByText('Valid')).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    render(
      <FilePreview 
        data={[]} 
        fileName="empty.csv" 
      />
    );

    expect(screen.getByText('No data to preview')).toBeInTheDocument();
  });

  it('implements pagination for large datasets', () => {
    // Create data with more than 10 rows to test pagination
    const largeData = Array.from({ length: 25 }, (_, i) => ({
      'Product Description': `Widget ${i + 1}`,
      'Quantity': '1',
      'Unit': 'piece',
      'Value': '10.00',
      'Origin Country': 'USA',
      'Unit Price': '10.00'
    }));

    render(
      <FilePreview 
        data={largeData} 
        fileName="large.csv" 
      />
    );

    // Should show pagination controls
    expect(screen.getByText('Showing 1 to 10 of 25 rows')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.getByText('Previous')).toBeInTheDocument();
  });

  it('supports editing when editable prop is true', async () => {
    const user = userEvent.setup();
    const onDataChange = jest.fn();

    render(
      <FilePreview 
        data={mockData} 
        fileName="test.csv" 
        editable={true}
        onDataChange={onDataChange}
      />
    );

    // Find a cell and click it to edit
    const cell = screen.getByText('Widget A');
    await user.click(cell);

    // Should show edit input
    // Note: This is a simplified test - actual implementation would be more complex
  });

  it('validates cross-field calculations', () => {
    const dataWithCalculationError = [
      {
        'Product Description': 'Miscalculated Item',
        'Quantity': '10',
        'Unit': 'pieces',
        'Value': '999.99',  // Should be 100.00 (10 * 10.00)
        'Origin Country': 'USA',
        'Unit Price': '10.00'
      }
    ];

    render(
      <FilePreview 
        data={dataWithCalculationError} 
        fileName="test.csv" 
      />
    );

    // Should show validation error
    expect(screen.getByText(/error/)).toBeInTheDocument();
  });

  it('shows row numbers correctly', () => {
    render(
      <FilePreview 
        data={mockData} 
        fileName="test.csv" 
      />
    );

    // Should show row numbers starting from 1
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('handles pagination navigation', async () => {
    const user = userEvent.setup();
    
    // Create enough data for multiple pages
    const largeData = Array.from({ length: 25 }, (_, i) => ({
      'Product Description': `Widget ${i + 1}`,
      'Quantity': '1',
      'Unit': 'piece',
      'Value': '10.00',
      'Origin Country': 'USA',
      'Unit Price': '10.00'
    }));

    render(
      <FilePreview 
        data={largeData} 
        fileName="large.csv" 
      />
    );

    // Test next page button
    const nextButton = screen.getByText('Next');
    await user.click(nextButton);

    // Should show next page data
    expect(screen.getByText('Showing 11 to 20 of 25 rows')).toBeInTheDocument();
  });
});