/**
 * Client-side file validation utilities for immediate feedback
 */

interface ValidationError {
  field: string;
  error: string;
  row?: number;
  column?: string;
}

interface ClientValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: string[];
  canUpload: boolean;
}

const REQUIRED_COLUMNS = [
  '№',
  'Наименование товара',
  'Страна происхождения',
  'Количество мест',
  'Часть мест',
  'Вид упаковки',
  'Количество',
  'Единица измерение',
  'Цена',
  'Брутто кг',
  'Нетто кг',
  'Процедура',
  'Преференция',
  'BKU',
  'Количество в допольнительной ед. изм.',
  'Допольнительная ед. изм.'
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const SUPPORTED_TYPES = ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
const SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];

/**
 * Perform immediate client-side validation
 */
export function performClientValidation(file: File): ClientValidationResult {
  console.log('🔍 Client-side validation starting for file:', file.name);
  const errors: ValidationError[] = [];
  const warnings: string[] = [];

  // File size validation
  if (file.size > MAX_FILE_SIZE) {
    errors.push({
      field: 'file_size',
      error: `File size (${Math.round(file.size / 1024 / 1024)}MB) exceeds maximum allowed size of 10MB`
    });
  }

  // File type validation
  const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
  const isValidType = SUPPORTED_TYPES.includes(file.type) || SUPPORTED_EXTENSIONS.includes(fileExtension);
  
  if (!isValidType) {
    errors.push({
      field: 'file_type',
      error: `Unsupported file type. Only CSV and Excel files (.csv, .xlsx, .xls) are allowed. Detected type: ${file.type || 'unknown'}`
    });
  }

  // File name validation
  if (!file.name.trim()) {
    errors.push({
      field: 'file_name',
      error: 'File must have a valid name'
    });
  }

  // Check for potential encoding issues (CSV only)
  if (fileExtension === '.csv' && file.type !== 'text/csv') {
    warnings.push('CSV file may have encoding issues. Ensure the file is saved with UTF-8 encoding.');
  }

  // Large file warning
  if (file.size > 5 * 1024 * 1024) { // 5MB
    warnings.push('Large file detected. Upload and validation may take longer than usual.');
  }

  const valid = errors.length === 0;
  const canUpload = valid;

  console.log(`📊 Client validation complete: ${errors.length} errors, ${warnings.length} warnings`);
  if (errors.length > 0) {
    console.log('❌ Validation errors:', errors);
  }
  if (warnings.length > 0) {
    console.log('⚠️ Validation warnings:', warnings);
  }

  return {
    valid,
    errors,
    warnings,
    canUpload
  };
}

/**
 * Parse CSV header row and validate required columns
 */
export async function validateCSVHeaders(file: File): Promise<{
  hasRequiredColumns: boolean;
  missingColumns: string[];
  detectedColumns: string[];
  warnings: string[];
}> {
  console.log('🔍 Validating CSV headers for file:', file.name);
  
  return new Promise((resolve) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const firstLine = text.split('\n')[0];
        const headers = firstLine.split(',').map(h => h.trim().replace(/["']/g, ''));
        
        console.log('📋 Detected headers:', headers);
        
        const missingColumns = REQUIRED_COLUMNS.filter(required => 
          !headers.includes(required)
        );

        const warnings = [];
        
        // Check for common column name variations
        const columnMapping: Record<string, string[]> = {
          '№': ['номер', 'number', 'no', '#'],
          'Наименование товара': ['товар', 'название', 'product', 'description', 'наименование', 'наименование товара'],
          'Страна происхождения': ['страна', 'происхождения', 'country', 'origin', 'страна происхождения'],
          'Количество мест': ['мест', 'места', 'packages', 'количество мест'],
          'Часть мест': ['часть', 'part', 'части', 'часть мест'],
          'Вид упаковки': ['упаковка', 'package', 'packaging', 'тара', 'вид упаковки'],
          'Количество': ['кол-во', 'qty', 'quantity', 'amount', 'количество'],
          'Единица измерение': ['ед.изм', 'единица', 'unit', 'measure', 'единицы', 'единица измерение'],
          'Цена': ['стоимость', 'price', 'cost', 'value', 'цена'],
          'Брутто кг': ['брутто', 'gross', 'вес брутто', 'брутто кг'],
          'Нетто кг': ['нетто', 'net', 'вес нетто', 'нетто кг'],
          'Процедура': ['procedure', 'процедуры', 'процедура'],
          'Преференция': ['preference', 'преференции', 'преференция'],
          'BKU': ['бку', 'bku'],
          'Количество в допольнительной ед. изм.': ['доп.кол-во', 'additional quantity', 'количество в допольнительной ед. изм.'],
          'Допольнительная ед. изм.': ['доп.ед.изм', 'additional unit', 'допольнительная ед. изм.']
        };

        for (const [required, variations] of Object.entries(columnMapping)) {
          if (missingColumns.includes(required)) {
            const foundVariation = headers.find(h => variations.some(v => h.includes(v)));
            if (foundVariation) {
              warnings.push(`Column "${foundVariation}" might be "${required}". Please verify column names match requirements.`);
            }
          }
        }

        console.log('📊 Header validation result:', {
          hasAllRequired: missingColumns.length === 0,
          missing: missingColumns,
          warnings: warnings.length
        });

        resolve({
          hasRequiredColumns: missingColumns.length === 0,
          missingColumns,
          detectedColumns: headers,
          warnings
        });
      } catch (error) {
        resolve({
          hasRequiredColumns: false,
          missingColumns: REQUIRED_COLUMNS,
          detectedColumns: [],
          warnings: ['Could not read file headers. Please ensure file is valid CSV format.']
        });
      }
    };

    reader.onerror = () => {
      resolve({
        hasRequiredColumns: false,
        missingColumns: REQUIRED_COLUMNS,
        detectedColumns: [],
        warnings: ['Error reading file. Please try again.']
      });
    };

    // Read only first 1KB for header validation
    const blob = file.slice(0, 1024);
    reader.readAsText(blob);
  });
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Get file type display name
 */
export function getFileTypeDisplay(file: File): string {
  const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
  
  switch (ext) {
    case '.csv':
      return 'CSV File';
    case '.xlsx':
      return 'Excel File (XLSX)';
    case '.xls':
      return 'Excel File (XLS)';
    default:
      return file.type || 'Unknown Format';
  }
}

/**
 * Validate numeric value
 */
export function validateNumeric(value: string): { valid: boolean; error?: string } {
  if (!value || value.trim() === '') {
    return { valid: false, error: 'Value is required' };
  }

  const num = parseFloat(value.replace(/,/g, ''));
  if (isNaN(num)) {
    return { valid: false, error: 'Must be a valid number' };
  }

  if (num <= 0) {
    return { valid: false, error: 'Must be greater than 0' };
  }

  return { valid: true };
}

/**
 * Validate text field
 */
export function validateTextField(value: string, minLength = 1, maxLength = 500): { valid: boolean; error?: string } {
  if (!value || value.trim() === '') {
    return { valid: false, error: 'Value is required' };
  }

  const trimmed = value.trim();
  if (trimmed.length < minLength) {
    return { valid: false, error: `Must be at least ${minLength} character${minLength !== 1 ? 's' : ''} long` };
  }

  if (trimmed.length > maxLength) {
    return { valid: false, error: `Must be no more than ${maxLength} characters long` };
  }

  return { valid: true };
}