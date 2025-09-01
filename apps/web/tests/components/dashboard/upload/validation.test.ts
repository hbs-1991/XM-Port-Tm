import {
  performClientValidation,
  validateCSVHeaders,
  formatFileSize,
  getFileTypeDisplay,
  validateNumeric,
  validateTextField
} from '@/components/dashboard/upload/validation';

// Mock File constructor for testing
const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['content'], name, { type });
  Object.defineProperty(file, 'size', { value: size, writable: false });
  return file;
};

describe('Client Validation Utilities', () => {
  describe('performClientValidation', () => {
    it('validates file size within limits', () => {
      const file = createMockFile('test.csv', 5 * 1024 * 1024, 'text/csv'); // 5MB
      const result = performClientValidation(file);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.canUpload).toBe(true);
    });

    it('rejects files exceeding size limit', () => {
      const file = createMockFile('large.csv', 15 * 1024 * 1024, 'text/csv'); // 15MB
      const result = performClientValidation(file);

      expect(result.valid).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].field).toBe('file_size');
      expect(result.errors[0].error).toContain('exceeds maximum allowed size');
      expect(result.canUpload).toBe(false);
    });

    it('validates supported file types', () => {
      const csvFile = createMockFile('test.csv', 1024, 'text/csv');
      const xlsxFile = createMockFile('test.xlsx', 1024, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');

      expect(performClientValidation(csvFile).valid).toBe(true);
      expect(performClientValidation(xlsxFile).valid).toBe(true);
    });

    it('rejects unsupported file types', () => {
      const file = createMockFile('test.txt', 1024, 'text/plain');
      const result = performClientValidation(file);

      expect(result.valid).toBe(false);
      expect(result.errors[0].field).toBe('file_type');
      expect(result.errors[0].error).toContain('Unsupported file type');
    });

    it('validates file extension when MIME type is unknown', () => {
      const csvFile = createMockFile('test.csv', 1024, '');
      const xlsxFile = createMockFile('test.xlsx', 1024, '');

      expect(performClientValidation(csvFile).valid).toBe(true);
      expect(performClientValidation(xlsxFile).valid).toBe(true);
    });

    it('rejects files without valid names', () => {
      const file = createMockFile('', 1024, 'text/csv');
      const result = performClientValidation(file);

      expect(result.valid).toBe(false);
      expect(result.errors[0].field).toBe('file_name');
      expect(result.errors[0].error).toBe('File must have a valid name');
    });

    it('provides warnings for large files', () => {
      const file = createMockFile('large.csv', 7 * 1024 * 1024, 'text/csv'); // 7MB
      const result = performClientValidation(file);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain('Large file detected. Upload and validation may take longer than usual.');
    });

    it('warns about potential CSV encoding issues', () => {
      const file = createMockFile('test.csv', 1024, 'application/octet-stream');
      const result = performClientValidation(file);

      expect(result.warnings).toContain('CSV file may have encoding issues. Ensure the file is saved with UTF-8 encoding.');
    });

    it('handles multiple validation errors', () => {
      const file = createMockFile('', 15 * 1024 * 1024, 'text/plain');
      const result = performClientValidation(file);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(1);
      expect(result.canUpload).toBe(false);
    });
  });

  describe('validateCSVHeaders', () => {
    // Mock FileReader for header validation tests
    const mockFileReader = (content: string) => {
      const mockReader = {
        onload: null as any,
        onerror: null as any,
        readAsText: jest.fn(),
        result: content
      };

      // Simulate successful read
      setTimeout(() => {
        if (mockReader.onload) {
          mockReader.onload({ target: { result: content } });
        }
      }, 0);

      return mockReader;
    };

    beforeEach(() => {
      // Mock FileReader
      global.FileReader = jest.fn(() => mockFileReader('Product Description,Quantity,Unit,Value,Origin Country,Unit Price\ntest,1,kg,10,US,10')) as any;
    });

    it('validates CSV with all required headers', async () => {
      const file = createMockFile('test.csv', 1024, 'text/csv');
      const result = await validateCSVHeaders(file);

      expect(result.hasRequiredColumns).toBe(true);
      expect(result.missingColumns).toHaveLength(0);
      expect(result.detectedColumns).toContain('product description');
      expect(result.warnings).toHaveLength(0);
    });

    it('detects missing required columns', async () => {
      global.FileReader = jest.fn(() => mockFileReader('Description,Qty\ntest,1')) as any;
      
      const file = createMockFile('test.csv', 1024, 'text/csv');
      const result = await validateCSVHeaders(file);

      expect(result.hasRequiredColumns).toBe(false);
      expect(result.missingColumns.length).toBeGreaterThan(0);
      expect(result.missingColumns).toContain('unit');
      expect(result.missingColumns).toContain('value');
    });

    it('provides suggestions for similar column names', async () => {
      global.FileReader = jest.fn(() => mockFileReader('Description,Qty,Price,Country\ntest,1,10,US')) as any;
      
      const file = createMockFile('test.csv', 1024, 'text/csv');
      const result = await validateCSVHeaders(file);

      expect(result.warnings.length).toBeGreaterThan(0);
      expect(result.warnings.some(w => w.includes('might be'))).toBe(true);
    });

    it('handles file read errors gracefully', async () => {
      const mockErrorReader = {
        onload: null as any,
        onerror: null as any,
        readAsText: jest.fn(),
        result: null
      };

      setTimeout(() => {
        if (mockErrorReader.onerror) {
          mockErrorReader.onerror(new Error('Read failed'));
        }
      }, 0);

      global.FileReader = jest.fn(() => mockErrorReader) as any;
      
      const file = createMockFile('test.csv', 1024, 'text/csv');
      const result = await validateCSVHeaders(file);

      expect(result.hasRequiredColumns).toBe(false);
      expect(result.warnings).toContain('Error reading file. Please try again.');
    });

    it('handles malformed CSV content', async () => {
      global.FileReader = jest.fn(() => mockFileReader('invalid csv content without proper structure')) as any;
      
      const file = createMockFile('test.csv', 1024, 'text/csv');
      const result = await validateCSVHeaders(file);

      expect(result.hasRequiredColumns).toBe(false);
      expect(result.detectedColumns).toContain('invalid csv content without proper structure');
    });
  });

  describe('formatFileSize', () => {
    it('formats bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 Bytes');
      expect(formatFileSize(1024)).toBe('1 KB');
      expect(formatFileSize(1048576)).toBe('1 MB');
      expect(formatFileSize(1073741824)).toBe('1 GB');
    });

    it('formats decimal values correctly', () => {
      expect(formatFileSize(1536)).toBe('1.5 KB');
      expect(formatFileSize(2621440)).toBe('2.5 MB');
    });

    it('handles large file sizes', () => {
      const largeSize = 15 * 1024 * 1024; // 15MB
      expect(formatFileSize(largeSize)).toBe('15 MB');
    });
  });

  describe('getFileTypeDisplay', () => {
    it('returns correct display names for supported formats', () => {
      expect(getFileTypeDisplay(createMockFile('test.csv', 1024, 'text/csv'))).toBe('CSV File');
      expect(getFileTypeDisplay(createMockFile('test.xlsx', 1024, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))).toBe('Excel File (XLSX)');
      expect(getFileTypeDisplay(createMockFile('test.xls', 1024, 'application/vnd.ms-excel'))).toBe('Excel File (XLS)');
    });

    it('falls back to MIME type for unknown extensions', () => {
      expect(getFileTypeDisplay(createMockFile('test.unknown', 1024, 'application/custom'))).toBe('application/custom');
    });

    it('handles files without MIME type', () => {
      expect(getFileTypeDisplay(createMockFile('test.unknown', 1024, ''))).toBe('Unknown Format');
    });
  });

  describe('validateNumeric', () => {
    it('validates positive numbers', () => {
      expect(validateNumeric('123').valid).toBe(true);
      expect(validateNumeric('45.67').valid).toBe(true);
      expect(validateNumeric('1,234.56').valid).toBe(true); // With comma separator
    });

    it('rejects zero and negative numbers', () => {
      expect(validateNumeric('0').valid).toBe(false);
      expect(validateNumeric('-10').valid).toBe(false);
      expect(validateNumeric('0').error).toBe('Must be greater than 0');
    });

    it('rejects non-numeric values', () => {
      expect(validateNumeric('abc').valid).toBe(false);
      expect(validateNumeric('').valid).toBe(false);
      expect(validateNumeric('   ').valid).toBe(false);
      expect(validateNumeric('abc').error).toBe('Must be a valid number');
    });

    it('handles edge cases', () => {
      expect(validateNumeric('0.001').valid).toBe(true);
      expect(validateNumeric('999999').valid).toBe(true);
      expect(validateNumeric('1e5').valid).toBe(true); // Scientific notation
    });
  });

  describe('validateTextField', () => {
    it('validates non-empty text within length limits', () => {
      expect(validateTextField('Valid text').valid).toBe(true);
      expect(validateTextField('A').valid).toBe(true);
    });

    it('rejects empty or whitespace-only text', () => {
      expect(validateTextField('').valid).toBe(false);
      expect(validateTextField('   ').valid).toBe(false);
      expect(validateTextField('').error).toBe('Value is required');
    });

    it('validates minimum length requirements', () => {
      expect(validateTextField('AB', 3).valid).toBe(false);
      expect(validateTextField('ABC', 3).valid).toBe(true);
      expect(validateTextField('AB', 3).error).toBe('Must be at least 3 characters long');
    });

    it('validates maximum length requirements', () => {
      const longText = 'A'.repeat(600);
      expect(validateTextField(longText, 1, 500).valid).toBe(false);
      expect(validateTextField(longText, 1, 500).error).toBe('Must be no more than 500 characters long');
    });

    it('handles custom length requirements', () => {
      expect(validateTextField('Test', 2, 10).valid).toBe(true);
      expect(validateTextField('A', 2, 10).valid).toBe(false);
      expect(validateTextField('A'.repeat(15), 2, 10).valid).toBe(false);
    });

    it('trims whitespace before validation', () => {
      expect(validateTextField('  Valid  ', 3).valid).toBe(true);
      expect(validateTextField('  AB  ', 3).valid).toBe(false); // Trimmed length is 2
    });
  });
});