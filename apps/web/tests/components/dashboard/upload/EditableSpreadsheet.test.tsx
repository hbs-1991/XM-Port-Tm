import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditableSpreadsheet } from '@/components/dashboard/upload/EditableSpreadsheet';

// Mock data
const mockData = [
  {
    'Product Description': 'Test Product 1',
    'Quantity': 10,
    'Unit': 'pcs',
    'Value': 1000.00,
    'Origin Country': 'USA',
    'Unit Price': 100.00
  },
  {
    'Product Description': 'Test Product 2',
    'Quantity': 5,
    'Unit': 'kg',
    'Value': 250.00,
    'Origin Country': 'Canada',
    'Unit Price': 50.00
  }
];

// Mock functions
const mockOnDataChange = jest.fn();
const mockOnSave = jest.fn();

describe('EditableSpreadsheet Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    test('renders with data', () => {
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText('Editable Spreadsheet - test.csv')).toBeInTheDocument();
      expect(screen.getByText('Test Product 1')).toBeInTheDocument();
      expect(screen.getByText('Test Product 2')).toBeInTheDocument();
      expect(screen.getByText('2 rows')).toBeInTheDocument();
    });

    test('renders in read-only mode', () => {
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          readOnly={true}
        />
      );

      expect(screen.getByText('Data Preview - test.csv')).toBeInTheDocument();
      expect(screen.queryByText('Add Row')).not.toBeInTheDocument();
      expect(screen.queryByText('Actions')).not.toBeInTheDocument();
    });

    test('renders empty state correctly', () => {
      render(
        <EditableSpreadsheet
          data={[]}
          fileName="empty.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText('No data to preview')).toBeInTheDocument();
      expect(screen.getByText('Add First Row')).toBeInTheDocument();
    });

    test('shows validation badge correctly', () => {
      const invalidData = [
        {
          'Product Description': '',  // Empty required field
          'Quantity': -5,  // Negative number
          'Unit': 'pcs',
          'Value': 250.00,
          'Origin Country': 'USA',
          'Unit Price': 50.00
        }
      ];

      render(
        <EditableSpreadsheet
          data={invalidData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText(/error/)).toBeInTheDocument();
    });
  });

  describe('Inline Editing', () => {
    test('allows editing cells when not read-only', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Find the first product description cell and click it
      const productCell = screen.getByText('Test Product 1');
      await user.click(productCell);

      // Should show input field
      const input = screen.getByDisplayValue('Test Product 1');
      expect(input).toBeInTheDocument();

      // Edit the value
      await user.clear(input);
      await user.type(input, 'Updated Product 1');

      // Save the edit - look for button with Save icon or text
      const saveButton = screen.getByTitle('Save edit');
      await user.click(saveButton);

      // Should call onDataChange with updated data
      expect(mockOnDataChange).toHaveBeenCalledWith([
        {
          ...mockData[0],
          'Product Description': 'Updated Product 1'
        },
        mockData[1]
      ]);
    });

    test('cancels edit on escape key', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Start editing
      const productCell = screen.getByText('Test Product 1');
      await user.click(productCell);

      const input = screen.getByDisplayValue('Test Product 1');
      await user.clear(input);
      await user.type(input, 'New Value');

      // Press escape
      fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });

      // Should not call onDataChange and should close edit mode
      expect(mockOnDataChange).not.toHaveBeenCalled();
      expect(screen.queryByDisplayValue('New Value')).not.toBeInTheDocument();
    });

    test('saves edit on enter key', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Start editing
      const productCell = screen.getByText('Test Product 1');
      await user.click(productCell);

      const input = screen.getByDisplayValue('Test Product 1');
      await user.clear(input);
      await user.type(input, 'Enter Product{enter}');

      // Should call onDataChange
      await waitFor(() => {
        expect(mockOnDataChange).toHaveBeenCalled();
      });
    });

    test('converts numeric fields correctly', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Edit quantity field
      const quantityCell = screen.getByText('10');
      await user.click(quantityCell);

      const input = screen.getByDisplayValue('10');
      await user.clear(input);
      await user.type(input, '15');

      const saveButton = screen.getByTitle('Save edit');
      await user.click(saveButton);

      // Should convert to number
      expect(mockOnDataChange).toHaveBeenCalledWith([
        {
          ...mockData[0],
          'Quantity': 15
        },
        mockData[1]
      ]);
    });
  });

  describe('Row Manipulation', () => {
    test('adds new row', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      const addButton = screen.getByText('Add Row');
      await user.click(addButton);

      expect(mockOnDataChange).toHaveBeenCalledWith([
        ...mockData,
        {
          'Product Description': '',
          'Quantity': 0,
          'Unit': '',
          'Value': 0,
          'Origin Country': '',
          'Unit Price': 0
        }
      ]);
    });

    test('deletes row', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Find delete button for first row (using title attribute)
      const deleteButtons = screen.getAllByTitle('Delete row');
      await user.click(deleteButtons[0]);

      expect(mockOnDataChange).toHaveBeenCalledWith([mockData[1]]);
    });

    test('duplicates row', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Find duplicate button for first row
      const duplicateButtons = screen.getAllByTitle('Duplicate row');
      await user.click(duplicateButtons[0]);

      expect(mockOnDataChange).toHaveBeenCalledWith([
        mockData[0],
        { ...mockData[0] }, // Duplicated row
        mockData[1]
      ]);
    });

    test('prevents deletion when only one row remains', () => {
      const singleRowData = [mockData[0]];
      
      render(
        <EditableSpreadsheet
          data={singleRowData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      const deleteButton = screen.getByTitle('Delete row');
      expect(deleteButton).toBeDisabled();
    });

    test('prevents adding rows when max reached', () => {
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
          maxRows={2}
        />
      );

      const addButton = screen.getByText('Add Row');
      expect(addButton).toBeDisabled();
    });
  });

  describe('Save Functionality', () => {
    test('shows save button when data changes', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
          onSave={mockOnSave}
        />
      );

      // Initially no save button
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();

      // Make a change
      const productCell = screen.getByText('Test Product 1');
      await user.click(productCell);

      const input = screen.getByDisplayValue('Test Product 1');
      await user.clear(input);
      await user.type(input, 'Modified Product');

      const saveEditButton = screen.getByTitle('Save edit');
      await user.click(saveEditButton);

      // Now save button should appear
      expect(screen.getByText('Save Changes')).toBeInTheDocument();
    });

    test('calls onSave when save button clicked', async () => {
      const user = userEvent.setup();
      mockOnSave.mockResolvedValue(undefined);
      
      const { rerender } = render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
          onSave={mockOnSave}
        />
      );

      // Simulate data change by rerendering with modified data
      const modifiedData = [
        { ...mockData[0], 'Product Description': 'Modified Product' },
        mockData[1]
      ];

      rerender(
        <EditableSpreadsheet
          data={modifiedData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
          onSave={mockOnSave}
        />
      );

      // Manually set hasChanges state by simulating the change
      const productCell = screen.getByText('Modified Product');
      await user.click(productCell);

      const input = screen.getByDisplayValue('Modified Product');
      await user.clear(input);
      await user.type(input, 'Modified Product 2');

      const saveEditButton = screen.getByTitle('Save edit');
      await user.click(saveEditButton);

      // Click save changes button
      const saveChangesButton = screen.getByText('Save Changes');
      await user.click(saveChangesButton);

      expect(mockOnSave).toHaveBeenCalled();
    });

    test('resets changes', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Make a change to trigger reset button
      const productCell = screen.getByText('Test Product 1');
      await user.click(productCell);

      const input = screen.getByDisplayValue('Test Product 1');
      await user.clear(input);
      await user.type(input, 'Modified Product');

      const saveEditButton = screen.getByTitle('Save edit');
      await user.click(saveEditButton);

      // Click reset button
      const resetButton = screen.getByText('Reset');
      await user.click(resetButton);

      // Should call onDataChange with original data
      expect(mockOnDataChange).toHaveBeenLastCalledWith(mockData);
    });
  });

  describe('Validation', () => {
    test('shows validation errors for invalid data', () => {
      const invalidData = [
        {
          'Product Description': '',
          'Quantity': -5,
          'Unit': 'pcs',
          'Value': 250.00,
          'Origin Country': '',
          'Unit Price': 50.00
        }
      ];

      render(
        <EditableSpreadsheet
          data={invalidData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText('Required field is empty')).toBeInTheDocument();
      expect(screen.getByText('Must be greater than 0')).toBeInTheDocument();
    });

    test('validates cross-field calculations', () => {
      const invalidData = [
        {
          'Product Description': 'Test Product',
          'Quantity': 10,
          'Unit': 'pcs',
          'Value': 999.00, // Should be 1000 (10 * 100)
          'Origin Country': 'USA',
          'Unit Price': 100.00
        }
      ];

      render(
        <EditableSpreadsheet
          data={invalidData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText(/Value should be approximately/)).toBeInTheDocument();
    });

    test('disables save when validation errors exist', async () => {
      const user = userEvent.setup();
      
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
          onSave={mockOnSave}
        />
      );

      // Create validation error by editing to empty value
      const productCell = screen.getByText('Test Product 1');
      await user.click(productCell);

      const input = screen.getByDisplayValue('Test Product 1');
      await user.clear(input);

      const saveEditButton = screen.getByTitle('Save edit');
      await user.click(saveEditButton);

      // Save Changes button should be disabled
      const saveChangesButton = screen.getByText('Save Changes');
      expect(saveChangesButton).toBeDisabled();
    });
  });

  describe('Pagination', () => {
    test('shows pagination for large datasets', () => {
      // Create data with more than 20 rows
      const largeData = Array.from({ length: 25 }, (_, i) => ({
        'Product Description': `Product ${i + 1}`,
        'Quantity': 1,
        'Unit': 'pcs',
        'Value': 10.00,
        'Origin Country': 'USA',
        'Unit Price': 10.00
      }));

      render(
        <EditableSpreadsheet
          data={largeData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText('Showing 1 to 20 of 25 rows')).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
    });

    test('navigates between pages', async () => {
      const user = userEvent.setup();
      
      // Create data with more than 20 rows
      const largeData = Array.from({ length: 25 }, (_, i) => ({
        'Product Description': `Product ${i + 1}`,
        'Quantity': 1,
        'Unit': 'pcs',
        'Value': 10.00,
        'Origin Country': 'USA',
        'Unit Price': 10.00
      }));

      render(
        <EditableSpreadsheet
          data={largeData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      // Click next page
      const nextButton = screen.getByText('Next');
      await user.click(nextButton);

      expect(screen.getByText('Showing 21 to 25 of 25 rows')).toBeInTheDocument();
      expect(screen.getByText('Product 21')).toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    test('shows export button', () => {
      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      expect(screen.getByText('Export CSV')).toBeInTheDocument();
    });

    test('exports CSV data', async () => {
      const user = userEvent.setup();
      
      // Mock URL.createObjectURL and createElement
      const mockCreateObjectURL = jest.fn(() => 'blob:url');
      const mockClick = jest.fn();
      const mockLink = {
        href: '',
        download: '',
        click: mockClick
      };

      global.URL.createObjectURL = mockCreateObjectURL;
      jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);

      render(
        <EditableSpreadsheet
          data={mockData}
          fileName="test.csv"
          onDataChange={mockOnDataChange}
        />
      );

      const exportButton = screen.getByText('Export CSV');
      await user.click(exportButton);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
      expect(mockLink.download).toBe('edited_test.csv');
    });
  });
});