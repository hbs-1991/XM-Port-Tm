/**
 * File Processing Service
 * Separates preview data handling from backend processing to ensure complete files are processed
 */

import { getOptimalPreviewSize, previewPerformanceTracker } from './preview-config';
import { generateProcessingSummary } from './backend-verification';

export interface FileMetadata {
  name: string;
  size: number;
  type: string;
  lastModified: number;
  totalRows?: number;
}

export interface ProcessingMetadata {
  fileId: string;
  totalRows: number;
  previewRows: number;
  processingBatches: number;
  estimatedTime: number;
  isPreviewLimited: boolean;
}

export interface FilePreviewData {
  data: any[];
  metadata: ProcessingMetadata;
  summary: {
    canProcess: boolean;
    message: string;
    details: string[];
    warnings: string[];
  };
}

/**
 * Enhanced file processing service that separates preview from processing
 */
export class FileProcessingService {
  /**
   * Process file for preview while tracking full file metadata
   */
  async processFileForPreview(file: File): Promise<FilePreviewData> {
    const fileId = `${file.name}-${file.size}-${Date.now()}`;
    const timings = previewPerformanceTracker.startTracking(fileId);
    
    try {
      // Get optimal preview size based on file characteristics
      const optimalPreviewSize = getOptimalPreviewSize({ 
        fileSize: file.size 
      });
      
      // Parse file for preview data
      const { previewData, totalRows } = await this.parseFileContent(file, optimalPreviewSize);
      
      // Track performance
      previewPerformanceTracker.endTracking(fileId, timings, previewData.length);
      
      // Generate processing metadata
      const metadata: ProcessingMetadata = {
        fileId,
        totalRows,
        previewRows: previewData.length,
        processingBatches: Math.ceil(totalRows / 100), // Backend batch size is 100
        estimatedTime: this.estimateProcessingTime(totalRows),
        isPreviewLimited: previewData.length < totalRows
      };
      
      // Generate summary for user
      const processingSummary = generateProcessingSummary(
        totalRows, 
        file.size, 
        this.getFileExtension(file.name)
      );
      
      return {
        data: previewData,
        metadata,
        summary: {
          canProcess: processingSummary.canProcess,
          message: processingSummary.summary,
          details: processingSummary.details,
          warnings: processingSummary.warnings
        }
      };
      
    } catch (error) {
      previewPerformanceTracker.endTracking(fileId, timings, 0);
      throw new Error(`Failed to process file for preview: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
  
  /**
   * Parse file content and return both preview data and total row count
   */
  private async parseFileContent(
    file: File, 
    maxPreviewRows: number
  ): Promise<{ previewData: any[], totalRows: number }> {
    const extension = this.getFileExtension(file.name);
    
    if (extension === 'csv') {
      return this.parseCSVContent(file, maxPreviewRows);
    } else if (extension === 'xlsx' || extension === 'xls') {
      return this.parseExcelContent(file, maxPreviewRows);
    } else {
      throw new Error(`Unsupported file type: ${extension}`);
    }
  }
  
  /**
   * Parse CSV content and return preview + total count
   */
  private async parseCSVContent(
    file: File, 
    maxPreviewRows: number
  ): Promise<{ previewData: any[], totalRows: number }> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const lines = text.split(/\r?\n/).filter(line => line.trim());
          
          if (lines.length <= 1) {
            resolve({ previewData: [], totalRows: 0 });
            return;
          }
          
          const totalRows = lines.length - 1; // Exclude header
          const headers = this.parseCSVLine(lines[0]);
          
          // Parse preview data
          const previewLines = lines.slice(1, Math.min(maxPreviewRows + 1, lines.length));
          const previewData = previewLines.map(line => {
            const values = this.parseCSVLine(line);
            const row: any = {};
            
            headers.forEach((header, index) => {
              const value = values[index] || '';
              // Try to parse numbers for specific columns
              if (['Quantity', 'Value', 'Unit Price'].includes(header)) {
                const numValue = parseFloat(value);
                row[header] = isNaN(numValue) ? value : numValue;
              } else {
                row[header] = value;
              }
            });
            
            return row;
          });
          
          resolve({ previewData, totalRows });
          
        } catch (error) {
          reject(error);
        }
      };
      
      reader.onerror = () => reject(new Error('Failed to read CSV file'));
      
      // For large files, read in chunks to get total row count efficiently
      if (file.size > 2 * 1024 * 1024) { // > 2MB
        // For very large files, we could implement streaming parsing here
        // For now, read the whole file but this could be optimized
        reader.readAsText(file);
      } else {
        reader.readAsText(file);
      }
    });
  }
  
  /**
   * Parse Excel content and return preview + total count
   */
  private async parseExcelContent(
    file: File, 
    maxPreviewRows: number
  ): Promise<{ previewData: any[], totalRows: number }> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async (e) => {
        try {
          // Dynamic import to reduce bundle size
          const XLSX = await import('xlsx');
          
          const data = e.target?.result;
          const workbook = XLSX.read(data, { type: 'array' });
          
          // Get the first worksheet
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          
          // Convert to JSON to get total row count
          const jsonData = XLSX.utils.sheet_to_json(worksheet);
          const totalRows = jsonData.length;
          
          // Get preview data
          const previewSize = Math.min(maxPreviewRows, totalRows);
          const previewData = jsonData.slice(0, previewSize).map((row: any) => {
            const processedRow: any = {};
            Object.keys(row).forEach(key => {
              processedRow[key.trim()] = row[key];
            });
            return processedRow;
          });
          
          resolve({ previewData, totalRows });
          
        } catch (error) {
          reject(error);
        }
      };
      
      reader.onerror = () => reject(new Error('Failed to read Excel file'));
      reader.readAsArrayBuffer(file);
    });
  }
  
  /**
   * Parse CSV line handling quotes properly
   */
  private parseCSVLine(line: string): string[] {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++; // Skip next quote
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    
    // Add last field
    if (current || line.endsWith(',')) {
      result.push(current.trim());
    }
    
    return result;
  }
  
  /**
   * Get file extension
   */
  private getFileExtension(filename: string): string {
    return filename.toLowerCase().split('.').pop() || '';
  }
  
  /**
   * Estimate processing time based on total rows
   */
  private estimateProcessingTime(totalRows: number): number {
    // Base time: 10 seconds for file validation
    let estimatedSeconds = 10;
    
    // HS matching time: ~3 seconds per 100 products
    const batches = Math.ceil(totalRows / 100);
    estimatedSeconds += batches * 3;
    
    // XML generation time: ~5-15 seconds based on size
    estimatedSeconds += Math.min(15, Math.max(5, totalRows / 200));
    
    return estimatedSeconds;
  }
  
  /**
   * Validate file before processing
   */
  async validateFile(file: File): Promise<{
    isValid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const errors: string[] = [];
    const warnings: string[] = [];
    
    // Check file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      errors.push(`File size ${(file.size / 1024 / 1024).toFixed(2)}MB exceeds 10MB limit`);
    }
    
    // Check file type
    const extension = this.getFileExtension(file.name);
    if (!['csv', 'xlsx', 'xls'].includes(extension)) {
      errors.push(`File type .${extension} not supported. Use CSV, XLSX, or XLS files.`);
    }
    
    // Check for very large files that might cause performance issues
    if (file.size > 5 * 1024 * 1024) {
      warnings.push('Large file detected. Processing may take several minutes.');
    }
    
    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }
  
  /**
   * Get processing status message for user
   */
  getProcessingStatusMessage(metadata: ProcessingMetadata): string {
    if (metadata.isPreviewLimited) {
      return `Showing ${metadata.previewRows} of ${metadata.totalRows} rows for preview. All ${metadata.totalRows} rows will be processed by the backend.`;
    } else {
      return `All ${metadata.totalRows} rows are shown and will be processed.`;
    }
  }
}

/**
 * Singleton instance
 */
export const fileProcessingService = new FileProcessingService();