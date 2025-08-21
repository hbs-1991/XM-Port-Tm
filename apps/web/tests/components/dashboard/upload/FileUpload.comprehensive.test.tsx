import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FileUpload } from '@/components/dashboard/upload/FileUpload';
import * as processingService from '@/services/processing';

// Mock the processing service
jest.mock('@/services/processing');
const mockUploadFile = processingService.uploadFile as jest.MockedFunction<typeof processingService.uploadFile>;
const mockValidateFile = processingService.validateFile as jest.MockedFunction<typeof processingService.validateFile>;

// Mock react-dropzone with more realistic behavior
const mockGetRootProps = jest.fn();
const mockGetInputProps = jest.fn();
const mockIsDragActive = jest.fn();
const mockIsDragAccept = jest.fn();
const mockIsDragReject = jest.fn();

jest.mock('react-dropzone', () => ({
  useDropzone: jest.fn(() => ({
    getRootProps: mockGetRootProps,
    getInputProps: mockGetInputProps,
    isDragActive: mockIsDragActive(),
    isDragAccept: mockIsDragAccept(),
    isDragReject: mockIsDragReject(),
    acceptedFiles: [],
    fileRejections: [],
  })),
}));

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('FileUpload - Comprehensive Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetRootProps.mockReturnValue({ 'data-testid': 'dropzone' });
    mockGetInputProps.mockReturnValue({ 'data-testid': 'file-input' });
    mockIsDragActive.mockReturnValue(false);
    mockIsDragAccept.mockReturnValue(false);
    mockIsDragReject.mockReturnValue(false);
  });

  // File Selection and Validation Tests

  describe('File Selection and Basic Validation', () => {
    it('should accept valid CSV files', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity,Unit,Value,Country\nTest,1,pc,100,US'], 'test.csv', {
        type: 'text/csv',
      });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(mockValidateFile).toHaveBeenCalledWith(csvFile);
      });
    });

    it('should accept valid XLSX files', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const xlsxFile = new File(['mock xlsx content'], 'test.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, xlsxFile);
      });

      await waitFor(() => {
        expect(mockValidateFile).toHaveBeenCalledWith(xlsxFile);
      });
    });

    it('should reject files with invalid extensions', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, invalidFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/only csv and xlsx files are allowed/i)).toBeInTheDocument();
      });

      expect(mockValidateFile).not.toHaveBeenCalled();
    });

    it('should reject files exceeding size limit', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      // Create a file that exceeds 10MB
      const largeContent = 'x'.repeat(11 * 1024 * 1024); // 11MB
      const largeFile = new File([largeContent], 'large.csv', { type: 'text/csv' });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, largeFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/file size exceeds 10mb limit/i)).toBeInTheDocument();
      });

      expect(mockValidateFile).not.toHaveBeenCalled();
    });
  });

  // Real-time Validation Tests

  describe('Real-time Validation', () => {
    it('should show validation progress during file validation', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'test.csv', { type: 'text/csv' });

      // Mock slow validation
      mockValidateFile.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          isValid: true,
          totalRows: 1,
          validRows: 1,
          errors: [],
          warnings: [],
        }), 1000))
      );

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      // Should show validation in progress
      expect(screen.getByText(/validating file/i)).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.queryByText(/validating file/i)).not.toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should display detailed validation errors', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Invalid,Content'], 'invalid.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: false,
        totalRows: 1,
        validRows: 0,
        errors: [
          { field: 'headers', row: 1, error: 'Missing required column: Product Description' },
          { field: 'headers', row: 1, error: 'Missing required column: Quantity' },
        ],
        warnings: ['File encoding detected as Windows-1252, converted to UTF-8'],
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/validation failed/i)).toBeInTheDocument();
        expect(screen.getByText(/missing required column: product description/i)).toBeInTheDocument();
        expect(screen.getByText(/missing required column: quantity/i)).toBeInTheDocument();
      });
    });

    it('should show data quality score', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'test.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 10,
        validRows: 8,
        errors: [],
        warnings: [],
        summary: {
          dataQualityScore: 85,
          totalErrors: 2,
          errorsByField: { quantity: 2 },
          errorsByType: { validation: 2 },
          mostCommonErrors: ['Invalid quantity format'],
        },
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/data quality: 85%/i)).toBeInTheDocument();
        expect(screen.getByText(/8 of 10 rows valid/i)).toBeInTheDocument();
      });
    });
  });

  // Upload Progress and State Management Tests

  describe('Upload Progress and State Management', () => {
    it('should show upload progress with cancel capability', async () => {
      const user = userEvent.setup();
      const onSuccess = jest.fn();
      renderWithQueryClient(<FileUpload onUploadSuccess={onSuccess} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'test.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      // Mock upload with progress
      let uploadResolve: (value: any) => void;
      mockUploadFile.mockImplementation(
        () => new Promise(resolve => {
          uploadResolve = resolve;
        })
      );

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      // Wait for validation to complete
      await waitFor(() => {
        expect(screen.getByText(/upload file/i)).toBeInTheDocument();
      });

      // Click upload
      const uploadButton = screen.getByText(/upload file/i);
      await act(async () => {
        await user.click(uploadButton);
      });

      // Should show upload progress
      expect(screen.getByText(/uploading file/i)).toBeInTheDocument();
      expect(screen.getByText(/cancel/i)).toBeInTheDocument();

      // Complete upload
      act(() => {
        uploadResolve({ jobId: 'test-job-id', message: 'Upload successful' });
      });

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith({ jobId: 'test-job-id', message: 'Upload successful' });
      });
    });

    it('should handle upload cancellation', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'test.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      // Mock long-running upload
      mockUploadFile.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/upload file/i)).toBeInTheDocument();
      });

      const uploadButton = screen.getByText(/upload file/i);
      await act(async () => {
        await user.click(uploadButton);
      });

      // Should show cancel button
      const cancelButton = screen.getByText(/cancel/i);
      expect(cancelButton).toBeInTheDocument();

      // Cancel upload
      await act(async () => {
        await user.click(cancelButton);
      });

      // Should reset to initial state
      await waitFor(() => {
        expect(screen.queryByText(/uploading file/i)).not.toBeInTheDocument();
        expect(screen.getByText(/drag & drop your file here/i)).toBeInTheDocument();
      });
    });

    it('should handle upload errors gracefully', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'test.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      mockUploadFile.mockRejectedValue(new Error('Upload failed: Server error'));

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/upload file/i)).toBeInTheDocument();
      });

      const uploadButton = screen.getByText(/upload file/i);
      await act(async () => {
        await user.click(uploadButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/upload failed: server error/i)).toBeInTheDocument();
        expect(screen.getByText(/try again/i)).toBeInTheDocument();
      });
    });
  });

  // Drag and Drop Tests

  describe('Drag and Drop Functionality', () => {
    it('should handle drag enter and leave events', () => {
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const dropzone = screen.getByTestId('dropzone');

      // Simulate drag enter
      mockIsDragActive.mockReturnValue(true);
      fireEvent.dragEnter(dropzone);

      // Should show drag active state
      expect(mockIsDragActive).toHaveBeenCalled();

      // Simulate drag leave
      mockIsDragActive.mockReturnValue(false);
      fireEvent.dragLeave(dropzone);
    });

    it('should provide visual feedback for accepted/rejected files during drag', () => {
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const dropzone = screen.getByTestId('dropzone');

      // Simulate drag with accepted file
      mockIsDragAccept.mockReturnValue(true);
      fireEvent.dragEnter(dropzone);

      // Should show accept state styling
      expect(mockIsDragAccept).toHaveBeenCalled();

      // Simulate drag with rejected file
      mockIsDragAccept.mockReturnValue(false);
      mockIsDragReject.mockReturnValue(true);
      fireEvent.dragEnter(dropzone);

      // Should show reject state styling
      expect(mockIsDragReject).toHaveBeenCalled();
    });

    it('should handle file drop events', async () => {
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'dropped.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      const dropzone = screen.getByTestId('dropzone');

      // Simulate file drop
      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [csvFile],
        },
      });

      await waitFor(() => {
        expect(mockValidateFile).toHaveBeenCalledWith(csvFile);
      });
    });
  });

  // Data Preview Tests

  describe('Data Preview Functionality', () => {
    it('should show data preview after successful validation', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity,Unit,Value,Country\nTest Product,100,pieces,500.00,USA'], 'test.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
        preview: [
          { 'Product': 'Test Product', 'Quantity': '100', 'Unit': 'pieces', 'Value': '500.00', 'Country': 'USA' }
        ],
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/data preview/i)).toBeInTheDocument();
        expect(screen.getByText('Test Product')).toBeInTheDocument();
        expect(screen.getByText('100')).toBeInTheDocument();
        expect(screen.getByText('pieces')).toBeInTheDocument();
      });
    });

    it('should handle pagination in data preview', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['content'], 'test.csv', { type: 'text/csv' });

      // Mock large dataset
      const mockPreviewData = Array.from({ length: 25 }, (_, i) => ({
        'Product': `Product ${i + 1}`,
        'Quantity': `${i + 1}`,
        'Unit': 'pieces',
        'Value': `${(i + 1) * 10}.00`,
        'Country': 'USA'
      }));

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 25,
        validRows: 25,
        errors: [],
        warnings: [],
        preview: mockPreviewData,
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/data preview/i)).toBeInTheDocument();
        // Should show first 10 rows by default
        expect(screen.getByText('Product 1')).toBeInTheDocument();
        expect(screen.getByText('Product 10')).toBeInTheDocument();
        expect(screen.queryByText('Product 11')).not.toBeInTheDocument();
      });

      // Should have pagination controls
      expect(screen.getByText(/next/i)).toBeInTheDocument();
    });
  });

  // Error Recovery and Retry Tests

  describe('Error Recovery and Retry', () => {
    it('should allow retry after validation failure', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Invalid'], 'test.csv', { type: 'text/csv' });

      // First validation fails
      mockValidateFile.mockRejectedValueOnce(new Error('Validation service error'));

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/validation failed/i)).toBeInTheDocument();
        expect(screen.getByText(/retry validation/i)).toBeInTheDocument();
      });

      // Mock successful retry
      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      const retryButton = screen.getByText(/retry validation/i);
      await act(async () => {
        await user.click(retryButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/upload file/i)).toBeInTheDocument();
      });

      expect(mockValidateFile).toHaveBeenCalledTimes(2);
    });

    it('should allow file replacement after error', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const invalidFile = new File(['Invalid'], 'invalid.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValueOnce({
        isValid: false,
        totalRows: 1,
        validRows: 0,
        errors: [{ field: 'headers', row: 1, error: 'Missing required columns' }],
        warnings: [],
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, invalidFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/validation failed/i)).toBeInTheDocument();
        expect(screen.getByText(/choose different file/i)).toBeInTheDocument();
      });

      // Replace with valid file
      const validFile = new File(['Product,Quantity\nTest,1'], 'valid.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValueOnce({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      await act(async () => {
        await user.upload(fileInput, validFile);
      });

      await waitFor(() => {
        expect(screen.getByText(/upload file/i)).toBeInTheDocument();
      });
    });
  });

  // Accessibility Tests

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const dropzone = screen.getByTestId('dropzone');
      expect(dropzone).toHaveAttribute('role', 'button');
      expect(dropzone).toHaveAttribute('aria-label', expect.stringContaining('file upload'));

      const fileInput = screen.getByTestId('file-input');
      expect(fileInput).toHaveAttribute('aria-label', expect.stringContaining('file input'));
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const dropzone = screen.getByTestId('dropzone');

      // Should be focusable
      await act(async () => {
        await user.tab();
      });
      expect(dropzone).toHaveFocus();

      // Should activate on Enter/Space
      await act(async () => {
        await user.keyboard('{Enter}');
      });

      // Should trigger file dialog (mocked behavior would be tested)
    });

    it('should provide screen reader announcements for state changes', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<FileUpload onUploadSuccess={jest.fn()} />);

      const csvFile = new File(['Product,Quantity\nTest,1'], 'test.csv', { type: 'text/csv' });

      mockValidateFile.mockResolvedValue({
        isValid: true,
        totalRows: 1,
        validRows: 1,
        errors: [],
        warnings: [],
      });

      const fileInput = screen.getByTestId('file-input');
      await act(async () => {
        await user.upload(fileInput, csvFile);
      });

      // Should have ARIA live regions for status updates
      await waitFor(() => {
        const statusRegion = screen.getByRole('status');
        expect(statusRegion).toHaveTextContent(/validation successful/i);
      });
    });
  });
});