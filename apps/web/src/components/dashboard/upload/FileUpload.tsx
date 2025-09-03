'use client';

import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/shared/ui/card';
import { Button } from '@/components/shared/ui/button';
import { Progress } from '@/components/shared/ui/progress';
import { Badge } from '@/components/shared/ui/badge';
import { Alert, AlertDescription } from '@/components/shared/ui/alert';
import { Upload, FileText, X, AlertCircle, CheckCircle2, FileSpreadsheet } from 'lucide-react';
import { uploadFile, completeJobAfterHSMatching } from '@/services/processing';
import hsMatchingService from '@/services/hsMatching';
import xmlGenerationService from '@/services/xmlGeneration';
import { ProcessingJob, ProcessingStatus, ProductWithHSCode, ConfidenceLevel } from '@shared/types';
import * as XLSX from 'xlsx';
import { FilePreview } from './FilePreview';
import { EditableSpreadsheet } from './EditableSpreadsheet';
import { UploadProgress } from './UploadProgress';
import { UploadValidation } from './UploadValidation';
import { performClientValidation, validateCSVHeaders } from './validation';
import { 
  getOptimalPreviewSize, 
  getUserPreviewPreferences, 
  getReadChunkSize,
  previewPerformanceTracker 
} from '@/lib/preview-config';
import { fileProcessingService } from '@/lib/file-processing-service';
import { findColumnMapping, COLUMN_MAPPINGS } from './columnMapping';

interface FileUploadProps {
  onUploadComplete?: (job: ProcessingJob) => void;
  onError?: (error: string) => void;
  countrySchema?: 'TKM';
}

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'validating' | 'validated' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  job?: ProcessingJob;
  previewData?: any[];
  validationResult?: any;
  xmlGenerating?: boolean;
  xmlDownloadUrl?: string;
  canRetry?: boolean;
  hsMatches?: any[];
  hasHSCodes?: boolean;
  processingMetadata?: {
    totalRows: number;
    previewRows: number;
    processingBatches: number;
    estimatedTime: number;
    isPreviewLimited: boolean;
    statusMessage: string;
  };
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_TYPES = {
  'text/csv': ['.csv'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls']
};

export function FileUpload({ onUploadComplete, onError, countrySchema = 'TKM' }: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const queryClient = useQueryClient();

  // Helper function to create ProductWithHSCode from file data and HS matches
  const createProductsWithHSCode = (fileData: any[], hsMatches: any[]): ProductWithHSCode[] => {
    // Helper function to determine confidence level
    const getConfidenceLevel = (confidence: number): ConfidenceLevel => {
      if (confidence >= 0.95) return 'High';
      if (confidence >= 0.8) return 'Medium';
      return 'Low';
    };

    return fileData.map((row: any, index: number) => {
      const match = hsMatches?.[index];
      const hsCode = match?.primary_match?.hs_code || '';
      const confidence = match?.primary_match?.confidence || 0;
      const alternativeCodes = match?.alternative_matches?.map((alt: any) => alt.hs_code) || [];
      
      return {
        id: `product-${index}`,
        product_description: row['Product Description'] || '',
        quantity: Number(row['Quantity']) || 0,
        unit: row['Unit'] || '',
        value: Number(row['Value']) || 0,
        origin_country: row['Origin Country'] || '',
        unit_price: Number(row['Unit Price']) || 0,
        hs_code: hsCode,
        confidence_score: confidence,
        confidence_level: getConfidenceLevel(confidence),
        alternative_hs_codes: alternativeCodes,
        requires_manual_review: confidence < 0.8,
        user_confirmed: false,
        vector_store_reasoning: match?.primary_match?.reasoning
      };
    });
  };

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (data, variables) => {
      console.log('Upload success data:', data, 'variables:', variables);
      const fileId = variables.fileId;
      const uploadedFile = uploadedFiles.find(f => f.id === fileId);
      
      // Preserve existing preview data if server doesn't return any
      const finalPreviewData = (data as any)?.previewData || uploadedFile?.previewData || [];
      
      // Transform FileUploadResponse to ProcessingJob format
      const uploadResponse = data as any;
      const transformedJob: ProcessingJob = {
        id: uploadResponse.job_id || '',
        status: uploadResponse.status as ProcessingStatus,
        input_file_name: uploadResponse.file_name || '',
        input_file_size: uploadResponse.file_size || 0,
        credits_used: uploadResponse.credits_used || 1,
        total_products: uploadResponse.total_products || 0,
        successful_matches: uploadResponse.successful_matches || 0,
        country_schema: countrySchema || 'USA',
        created_at: new Date().toISOString(),
        // Add other required fields with defaults
        userId: '',
        processing_time_ms: 0,
        average_confidence: 0
      };
      
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'completed' as const, 
                progress: 100, 
                job: transformedJob, 
                previewData: finalPreviewData 
              }
            : f
        )
      );
      
      console.log('Upload completed, transformed job:', transformedJob, 'preview data:', finalPreviewData);
      onUploadComplete?.(transformedJob);
    },
    onError: (error: any, variables) => {
      const fileId = variables.fileId;
      
      // Parse error message more intelligently
      let errorMessage = 'Upload failed';
      let isRetryable = false;
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (detail.message) {
          errorMessage = detail.message;
          isRetryable = detail.retry_suggested || detail.error === 'credit_reservation_conflict';
        }
      } else if (error.message) {
        errorMessage = error.message;
        // Check if it's a retryable error based on message content
        isRetryable = errorMessage.includes('try again') || errorMessage.includes('concurrent requests');
      }
      
      // Format user-friendly error messages
      if (errorMessage.includes('insufficient_credits') || errorMessage.includes('Insufficient credits')) {
        errorMessage = 'Insufficient credits. Please check your balance or upgrade your plan.';
      } else if (errorMessage.includes('credit_reservation_conflict')) {
        errorMessage = 'Upload temporarily unavailable due to high demand. Please try again in a moment.';
        isRetryable = true;
      } else if (errorMessage.includes('concurrent requests')) {
        errorMessage = 'Multiple uploads detected. Please wait and try again.';
        isRetryable = true;
      }
      
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'error', 
                error: errorMessage,
                // Add a retry flag for UI to show retry button
                ...(isRetryable && { canRetry: true })
              }
            : f
        )
      );
      onError?.(errorMessage);
    }
  });

  // Enhanced file validation with immediate feedback
  const validateFile = useCallback(async (file: File): Promise<string | null> => {
    // Immediate client-side validation
    const clientValidation = performClientValidation(file);
    if (!clientValidation.valid) {
      return clientValidation.errors[0]?.error || 'File validation failed';
    }

    // For CSV files, also check headers
    if (file.name.toLowerCase().endsWith('.csv')) {
      try {
        const headerValidation = await validateCSVHeaders(file);
        if (!headerValidation.hasRequiredColumns) {
          return `Missing required columns: ${headerValidation.missingColumns.join(', ')}`;
        }
        if (headerValidation.warnings.length > 0) {
          console.warn('CSV header validation warnings:', headerValidation.warnings);
        }
      } catch (error) {
        console.warn('Could not validate CSV headers:', error);
      }
    }

    return null;
  }, []);

  // Parse file content for immediate preview with smart sizing
  const parseFileContent = async (file: File, maxPreviewRows?: number): Promise<any[]> => {
    const fileId = `${file.name}-${file.size}`;
    const timings = previewPerformanceTracker.startTracking(fileId);
    
    // Get user preferences and determine optimal preview size
    const userPrefs = getUserPreviewPreferences();
    const optimalPreviewSize = maxPreviewRows || getOptimalPreviewSize({
      fileSize: file.size,
      userPreference: userPrefs.maxRows
    });
    
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      // Handle Excel files
      if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
        reader.onload = (e) => {
          try {
            const data = e.target?.result;
            const workbook = XLSX.read(data, { type: 'array' });
            
            // Get the first worksheet
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            
            // Convert to JSON
            const jsonData = XLSX.utils.sheet_to_json(worksheet);
            
            console.log('Excel data parsed:', jsonData);
            
            // Smart preview sizing based on file size and performance
            const finalPreviewSize = Math.min(optimalPreviewSize, jsonData.length);
            const previewData = jsonData.slice(0, finalPreviewSize);
            
            // Track performance
            previewPerformanceTracker.endTracking(fileId, timings, finalPreviewSize);
            
            // Ensure consistent column names
            const processedData = previewData.map((row: any) => {
              const processedRow: any = {};
              Object.keys(row).forEach(key => {
                // Map common variations to standard names
                const normalizedKey = key.trim();
                processedRow[normalizedKey] = row[key];
              });
              return processedRow;
            });
            
            console.log('Processed Excel preview:', processedData);
            resolve(processedData.length > 0 ? processedData : []);
          } catch (error) {
            console.error('Error parsing Excel file:', error);
            previewPerformanceTracker.endTracking(fileId, timings, 0);
            resolve([]);
          }
        };
        
        reader.readAsArrayBuffer(file);
      } 
      // Handle CSV files
      else if (file.name.toLowerCase().endsWith('.csv')) {
        reader.onload = (e) => {
          try {
            const text = e.target?.result as string;
            
            // Split by line, handling both \n and \r\n
            const lines = text.split(/\r?\n/).filter(line => line.trim());
            
            if (lines.length === 0) {
              console.log('No lines found in CSV');
              resolve([]);
              return;
            }
            
            // Parse headers - handle quoted values
            const parseCSVLine = (line: string): string[] => {
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
            };
            
            const headers = parseCSVLine(lines[0]);
            
            console.log('Parsed headers:', headers);
            
            // Smart preview sizing for CSV data
            const finalPreviewSize = Math.min(optimalPreviewSize, lines.length - 1);
            const dataRows = lines.slice(1, finalPreviewSize + 1);
            const data = dataRows.map((line, lineIndex) => {
              const values = parseCSVLine(line);
              const row: any = {};
              
              headers.forEach((header, index) => {
                const value = values[index] || '';
                // Try to parse numbers
                if (['Quantity', 'Value', 'Unit Price'].includes(header)) {
                  const numValue = parseFloat(value);
                  row[header] = isNaN(numValue) ? value : numValue;
                } else {
                  row[header] = value;
                }
              });
              
              console.log(`Row ${lineIndex}:`, row);
              return row;
            });
            
            console.log('Parsed data preview:', data);
            
            // Track performance
            previewPerformanceTracker.endTracking(fileId, timings, data.length);
            
            resolve(data.length > 0 ? data : []);
          } catch (error) {
            console.error('Error parsing CSV file:', error);
            previewPerformanceTracker.endTracking(fileId, timings, 0);
            resolve([]);
          }
        };
        
        reader.onerror = (error) => {
          console.error('FileReader error:', error);
          reject(new Error('Failed to read file'));
        };
        
        // Smart file reading based on preview needs and file size
        const sizeToRead = getReadChunkSize(file.size);
        reader.readAsText(file.slice(0, sizeToRead));
      } 
      else {
        console.log('Unknown file type');
        resolve([]);
      }
    });
  };

  // Handle file drop
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    console.log('onDrop called with:', { acceptedFiles, rejectedFiles });
    
    // Handle rejected files
    if (rejectedFiles && rejectedFiles.length > 0) {
      rejectedFiles.forEach((rejection) => {
        console.error('File rejected:', rejection);
        const errors = rejection.errors?.map((e: any) => e.message).join(', ');
        onError?.(`File rejected: ${errors || 'Invalid file'}`);
      });
      return;
    }
    
    acceptedFiles.forEach(async (file) => {
      console.log('Processing accepted file:', file);
      const validationError = await validateFile(file);
      if (validationError) {
        onError?.(validationError);
        return;
      }

      const fileId = `${file.name}-${Date.now()}`;
      
      // Process file using enhanced service that separates preview from processing
      const fileProcessingResult = await fileProcessingService.processFileForPreview(file);
      
      const { data: previewData, metadata, summary } = fileProcessingResult;
      
      console.log(`File processing result:`, {
        totalRows: metadata.totalRows,
        previewRows: metadata.previewRows,
        batches: metadata.processingBatches,
        isLimited: metadata.isPreviewLimited
      });
      
      // Debug log to check preview data
      console.log('Preview data for file:', file.name, previewData);
      
      const newFile: UploadedFile = {
        file,
        id: fileId,
        status: 'validating',
        progress: 0,
        previewData: previewData.length > 0 ? previewData : undefined,
        processingMetadata: {
          totalRows: metadata.totalRows,
          previewRows: metadata.previewRows,
          processingBatches: metadata.processingBatches,
          estimatedTime: metadata.estimatedTime,
          isPreviewLimited: metadata.isPreviewLimited,
          statusMessage: fileProcessingService.getProcessingStatusMessage(metadata)
        }
      };
      
      console.log('New file object:', newFile);

      setUploadedFiles(prev => [...prev, newFile]);
    });
  }, [validateFile, onError]);

  const { getRootProps, getInputProps, isDragActive, isDragReject, fileRejections, open } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
    preventDropOnDocument: true,
    onDragEnter: () => {
      console.log('Drag enter detected');
    },
    onDragLeave: () => {
      console.log('Drag leave detected');
    },
    onDragOver: () => {
      console.log('Drag over detected');
    },
    onDropAccepted: (files) => {
      console.log('Files accepted:', files);
    },
    onDropRejected: (fileRejections) => {
      console.log('Files rejected:', fileRejections);
    },
    onFileDialogCancel: () => {
      console.log('File dialog cancelled');
    },
    onFileDialogOpen: () => {
      console.log('File dialog opened');
    }
  });

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleValidationComplete = (fileId: string, result: any) => {
    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { 
              ...f, 
              status: result.valid ? 'validated' : 'error',
              validationResult: result,
              error: result.valid ? undefined : 'File validation failed'
            }
          : f
      )
    );
  };

  const initiateUpload = (fileId: string) => {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (!file || !file.validationResult?.valid) return;

    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'uploading', progress: 10 }
          : f
      )
    );

    uploadMutation.mutate({
      file: file.file,
      fileId,
      countrySchema,
      onProgress: (progress: number) => {
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileId 
              ? { ...f, progress: Math.min(progress, 90) }
              : f
          )
        );
      }
    });
  };

  const retryUpload = (fileId: string) => {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (!file) return;

    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'uploading', progress: 10, error: undefined }
          : f
      )
    );

    uploadMutation.mutate({
      file: file.file,
      fileId,
      countrySchema,
      onProgress: (progress: number) => {
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileId 
              ? { ...f, progress: Math.min(progress, 90) }
              : f
          )
        );
      }
    });
  };

  const initiateHSMatching = async (jobId: string) => {
    try {
      // Get uploaded file data to create batch matching request
      const file = uploadedFiles.find(f => f.job?.id === jobId);
      if (!file?.previewData || file.previewData.length === 0) {
        onError?.('No data available for HS matching');
        return;
      }

      // Find the correct column name for product description using column mapping
      const sampleRow = file.previewData[0];
      const availableHeaders = Object.keys(sampleRow);
      
      // Find product description column using the mapping system
      let productDescriptionKey: string | null = null;
      for (const header of availableHeaders) {
        const mapping = findColumnMapping(header);
        if (mapping?.canonical === 'product_name') {
          productDescriptionKey = header;
          break;
        }
      }
      
      if (!productDescriptionKey) {
        onError?.('Could not find product description column in uploaded file');
        return;
      }

      console.log(`Using column '${productDescriptionKey}' for product descriptions`);

      // Create batch request from preview data
      const products = file.previewData.map((row: any) => {
        const productDescription = row[productDescriptionKey] || '';
        
        // Validate product description before sending
        if (!productDescription || productDescription.trim().length < 5) {
          console.warn(`Empty or too short product description for row:`, row);
          return null;
        }
        
        return {
          product_description: productDescription.trim(),
          country: countrySchema,
          include_alternatives: true,
          confidence_threshold: 0.7
        };
      }).filter(product => product !== null); // Remove invalid products

      if (products.length === 0) {
        onError?.('No valid product descriptions found for HS matching');
        return;
      }

      console.log(`Sending ${products.length} products for HS matching:`, products.slice(0, 3));

      const result = await hsMatchingService.matchBatchProducts({
        products,
        country: countrySchema
      });
      
      console.log('HS matching completed:', result);
      
      // Update the file data with HS matches
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === file.id 
            ? { 
                ...f, 
                hsMatches: result,
                hasHSCodes: true
              }
            : f
        )
      );

      // Complete the job after HS matching
      if (file.job?.id) {
        try {
          console.log('Completing job after HS matching:', file.job.id);
          
          // Convert HS matching results to the format expected by the API
          // Need to match HS results with original product data from previewData
          const hsMatches = result.map((match: any, index: number) => {
            const originalRow = file.previewData[index] || {};
            
            // Find required fields from original data using column mapping
            let quantity = 0;
            let unit = '';
            let unitPrice = 0;
            let origin_country = '';
            
            console.log(`Processing row ${index}:`, originalRow);
            console.log(`Available headers:`, Object.keys(originalRow));
            
            // Map columns using column mapping logic with priority handling
            Object.keys(originalRow).forEach(header => {
              const mapping = findColumnMapping(header);
              console.log(`Header "${header}" (value: "${originalRow[header]}") -> mapping:`, mapping?.canonical);
              if (mapping) {
                switch (mapping.canonical) {
                  case 'quantity':
                    const currentValue = parseFloat(originalRow[header]) || 0;
                    // Prioritize main "Количество" over additional quantity, and non-zero values
                    if (header === 'Количество' || (quantity === 0 && currentValue > 0)) {
                      quantity = currentValue;
                      console.log(`✅ Set quantity from "${header}": ${quantity}`);
                    } else {
                      console.log(`⚠️ Skipped quantity from "${header}" (value: ${currentValue}) - already have: ${quantity}`);
                    }
                    break;
                  case 'unit':
                    // Prioritize main unit field "Единица измерение", avoid numeric procedure values
                    if (header === 'Единица измерение' || (unit === '' && header !== 'Процедура' && isNaN(Number(originalRow[header])))) {
                      unit = originalRow[header] || '';
                      console.log(`✅ Set unit from "${header}": ${unit}`);
                    } else {
                      console.log(`⚠️ Skipped unit from "${header}" (value: "${originalRow[header]}") - already have: "${unit}" or is numeric`);
                    }
                    break;
                  case 'unit_price':
                    unitPrice = parseFloat(originalRow[header]) || 0;
                    console.log(`✅ Set unit_price: ${unitPrice}`);
                    break;
                  case 'origin_country':
                    origin_country = originalRow[header] || '';
                    console.log(`✅ Set origin_country: ${origin_country}`);
                    break;
                }
              }
            });
            
            // Calculate total value for XML generation
            const totalValue = quantity * unitPrice;
            console.log(`Final values - quantity: ${quantity}, unitPrice: ${unitPrice}, totalValue: ${totalValue}, unit: ${unit}, origin_country: ${origin_country}`);
            
            // Validate required fields before creating result object
            if (!quantity || quantity <= 0) {
              console.error(`❌ Invalid quantity for row ${index}: ${quantity}`);
            }
            if (!unit) {
              console.error(`❌ Missing unit for row ${index}`);
            }
            if (!origin_country) {
              console.error(`❌ Missing origin_country for row ${index}`);
            }
            if (!totalValue || totalValue <= 0) {
              console.error(`❌ Invalid total value for row ${index}: ${totalValue}`);
            }
            
            const resultObject = {
              product_description: match.query,
              matched_hs_code: match.primary_match?.hs_code || 'ERROR',
              confidence_score: match.primary_match?.confidence || 0,
              code_description: match.primary_match?.code_description || '',
              chapter: match.primary_match?.chapter || '',
              section: match.primary_match?.section || '',
              processing_time_ms: match.processing_time_ms || 0,
              // Include required ProductMatch fields from original data
              quantity,
              unit_of_measure: unit,
              // Prefer passing unit_price and let backend compute value
              unit_price: unitPrice,
              value: totalValue, // kept for backward compatibility
              origin_country,
              // Packaging and weights
              packages_count: parseInt((originalRow as any)['Количество мест'] || (originalRow as any)['package_quantity'] || '1', 10) || 1,
              packages_part: (originalRow as any)['Часть мест'] || (originalRow as any)['package_part'] || '',
              packaging_kind_code: (originalRow as any)['Вид упаковки'] || (originalRow as any)['package_type'] || '',
              gross_weight: parseFloat((originalRow as any)['Брутто кг'] || (originalRow as any)['gross_weight'] || '') || 0,
              net_weight: parseFloat((originalRow as any)['Нетто кг'] || (originalRow as any)['net_weight'] || '') || 0,
              supplementary_quantity: ((v => isNaN(parseFloat(v)) ? undefined : parseFloat(v))(((originalRow as any)['Количество в дополнительной ед. изм.'] || (originalRow as any)['additional_quantity'] || '') as string)),
              supplementary_uom_code: (originalRow as any)['Дополнительная ед. изм.'] || (originalRow as any)['additional_unit'] || undefined,
            };
            
            console.log(`📦 Created result object for row ${index}:`, resultObject);
            return resultObject;
          });

          // Check if job is already completed to avoid duplicate completion calls
          if (file.job?.status === 'COMPLETED' || file.job?.status === 'COMPLETED_WITH_ERRORS' || file.job?.status === 'FAILED') {
            console.log(`Job ${file.job.id} is already in final status: ${file.job.status}, skipping completion call`);
            console.log('✅ Job was already completed, XML generation is available');
            return; // Early return to prevent duplicate completion
          }

          // Debug: Show what we're sending to the backend
          console.log(`🚀 Sending job completion for ${file.job.id} with ${hsMatches.length} matches:`, hsMatches);
          
          // Validate data before sending
          const validMatches = hsMatches.filter(match => {
            const hasPositiveValue = (typeof match.value === 'number' && match.value > 0) || (typeof match.unit_price === 'number' && match.unit_price > 0);
            const isValid = match.quantity > 0 && hasPositiveValue && !!match.unit_of_measure && !!match.origin_country;
            if (!isValid) {
              console.error(`❌ Invalid match data:`, match);
            }
            return isValid;
          });
          
          console.log(`✅ Sending ${validMatches.length} valid matches out of ${hsMatches.length} total`);

          const completionResult = await completeJobAfterHSMatching(
            file.job.id,
            validMatches,
            hsMatches.length > validMatches.length ? [`Filtered out ${hsMatches.length - validMatches.length} invalid matches`] : []
          );

          console.log('Job completion result:', completionResult);

          if (completionResult.success) {
            // Update the file with completion status
            setUploadedFiles(prev => 
              prev.map(f => 
                f.job?.id === file.job?.id
                  ? {
                      ...f,
                      job: {
                        ...f.job!,
                        status: completionResult.status as ProcessingStatus,
                        total_products: completionResult.total_products,
                        successful_matches: completionResult.successful_matches,
                        average_confidence: completionResult.average_confidence || 0,
                        processing_time_ms: completionResult.processing_time_ms,
                      }
                    }
                  : f
              )
            );
            
            console.log('✅ Job completed successfully, now XML generation is available');
          }
        } catch (completionError) {
          console.error('Error completing job after HS matching:', completionError);
          // Don't throw error here - HS matching was successful, just job completion failed
          // XML generation might still work if we manually set the status
        }
      }
      
    } catch (error) {
      console.error('Error starting HS matching:', error);
      onError?.('Failed to start HS code matching: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const initiateXMLGeneration = async (jobId: string) => {
    try {
      const result = await xmlGenerationService.generateXML(jobId, {
        country_schema: countrySchema as 'TKM',
        include_metadata: true,
        validate_output: true
      });
      
      console.log('XML generation started:', result);
      
      if (result.success) {
        // Update the file status to show XML is being generated
        setUploadedFiles(prev => 
          prev.map(f => 
            f.job?.id === jobId 
              ? { ...f, xmlGenerating: true, xmlDownloadUrl: result.download_url }
              : f
          )
        );
        
        // Show success message
        onUploadComplete?.({
          ...result,
          message: 'XML generation started successfully'
        } as any);
      } else {
        throw new Error(result.error_message || 'XML generation failed');
      }
      
    } catch (error) {
      console.error('Error starting XML generation:', error);
      onError?.('Failed to start XML generation: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  return (
    <div className="space-y-4">
      {/* Compact Two-Card Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Card 1: File Upload & Template */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Upload className="w-4 h-4" />
              Upload Trade Data File
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div
              {...getRootProps()}
              className={`
                relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all
                ${isDragActive 
                  ? 'border-primary bg-primary/5' 
                  : 'border-border hover:border-primary/50 hover:bg-gray-50 dark:hover:bg-gray-900'
                }
              `}
              style={{ minHeight: '120px' }}
            >
              <input {...getInputProps()} />
              
              <div className="flex flex-col items-center gap-2 pointer-events-none">
                <Upload className={`w-8 h-8 ${isDragActive ? 'text-primary' : 'text-muted-foreground'}`} />
                <div>
                  <p className="text-sm font-medium">
                    {isDragActive ? 'Drop file here' : 'Drop file or click to browse'}
                  </p>
                  <div className="flex gap-1 mt-1 justify-center">
                    {['CSV', 'XLSX', 'XLS'].map(format => (
                      <Badge key={format} variant="secondary" className="text-xs px-1 py-0">
                        {format}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              {isDragActive && (
                <div className="absolute inset-0 border-2 border-primary rounded-lg bg-primary/5 flex items-center justify-center pointer-events-none">
                  <Upload className="w-8 h-8 text-primary animate-bounce" />
                </div>
              )}
            </div>

            {/* Alternative file select button */}
            <div className="flex gap-2">
              <Button
                onClick={() => open()}
                className="flex-1 bg-black text-white hover:bg-gray-800 active:bg-gray-900 active:scale-95 transition-all duration-200 ease-in-out"
                size="sm"
              >
                <Upload className="w-4 h-4 mr-1" />
                Select File
              </Button>
            </div>

            {/* Template Download - Compact */}
            <div className="flex items-center justify-between p-2 bg-primary/5 rounded border">
              <div className="flex-1">
                <p className="text-xs font-medium">Нужен шаблон?</p>
                <p className="text-xs text-muted-foreground">CSV с обязательными колонками</p>
              </div>
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    const response = await fetch('/api/proxy/api/v1/processing/template/download');
                    if (!response.ok) {
                      throw new Error('Failed to download template');
                    }
                    
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'upload_template.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (error) {
                    console.error('Template download failed:', error);
                    // Fallback to client-side generation with Russian headers
                    const headers = ['№', 'Наименование товара', 'Страна происхождения', 'Количество мест', 'Часть мест', 'Вид упаковки', 'Количество', 'Единица измерение', 'Цена', 'Брутто кг', 'Нетто кг', 'Процедура', 'Преференция', 'BKU', 'Количество в допольнительной ед. изм.', 'Допольнительная ед. изм.'];
                    // Add UTF-8 BOM for proper Russian character support in Excel
                    const utf8BOM = '\uFEFF';
                    const csvContent = utf8BOM + headers.join(',') + '\n1,Пример товара,Россия,1,1,Коробки,100,шт,1000.00,10.5,9.8,40,ОР,123456,50,кг\n';
                    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'upload_template.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  }
                }}
                className="text-xs h-7 px-3 bg-black text-white hover:bg-gray-800 active:bg-gray-900 active:scale-95 transition-all duration-200 ease-in-out"
              >
                Скачать
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Requirements & Status */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileText className="w-4 h-4" />
              File Requirements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-1">
                {[
                  'Product Description',
                  'Quantity', 
                  'Unit',
                  'Value',
                  'Origin Country',
                  'Unit Price'
                ].map(column => (
                  <div key={column} className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                    <span className="text-xs text-foreground">{column}</span>
                  </div>
                ))}
              </div>
              <div className="text-xs text-muted-foreground flex items-center gap-1 pt-1 border-t">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                Required • Max 10MB
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-4">
          {uploadedFiles.map((uploadedFile) => (
            <Card key={uploadedFile.id} className="relative">
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <FileText className="w-8 h-8 text-blue-500 flex-shrink-0 mt-1" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                        {uploadedFile.file.name}
                      </h4>
                      <Button
                        size="sm"
                        onClick={() => removeFile(uploadedFile.id)}
                        className="bg-black text-white hover:bg-gray-800 active:bg-gray-900 active:scale-95 transition-all duration-200 ease-in-out"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-3">
                      <span>{(uploadedFile.file.size / 1024 / 1024).toFixed(2)} MB</span>
                      <span>{uploadedFile.file.type || 'Unknown type'}</span>
                      <Badge variant={
                        uploadedFile.status === 'completed' ? 'default' :
                        uploadedFile.status === 'error' ? 'destructive' :
                        uploadedFile.status === 'validated' ? 'secondary' :
                        'outline'
                      } className="text-xs">
                        {uploadedFile.status === 'validating' ? 'Validating...' :
                         uploadedFile.status === 'validated' ? 'Validated' :
                         uploadedFile.status === 'uploading' ? 'Uploading...' :
                         uploadedFile.status === 'processing' ? 'Processing...' :
                         uploadedFile.status === 'completed' ? 'Completed' :
                         uploadedFile.status === 'error' ? 'Error' : 'Pending'}
                      </Badge>
                    </div>

                    {/* Compact Real-time Validation */}
                    {(uploadedFile.status === 'validating' || uploadedFile.status === 'validated' || uploadedFile.status === 'error') && (
                      <UploadValidation 
                        file={uploadedFile.file}
                        onValidationComplete={(result) => handleValidationComplete(uploadedFile.id, result)}
                        className="mb-2"
                      />
                    )}

                    {/* Upload Action Button - Prominent blue button */}
                    {uploadedFile.status === 'validated' && uploadedFile.validationResult?.valid && (
                      <div className="mb-3">
                        <Button
                          onClick={() => initiateUpload(uploadedFile.id)}
                          className="w-full bg-black text-white hover:bg-gray-800 active:bg-gray-900 active:scale-95 font-medium py-3 text-base shadow-md hover:shadow-lg transition-all duration-200 ease-in-out"
                          size="lg"
                        >
                          <Upload className="w-5 h-5 mr-2" />
                          Upload File for Processing
                        </Button>
                      </div>
                    )}

                    {/* Upload Progress */}
                    {uploadedFile.status === 'uploading' && (
                      <UploadProgress 
                        progress={uploadedFile.progress}
                        fileName={uploadedFile.file.name}
                        onCancel={() => removeFile(uploadedFile.id)}
                      />
                    )}

                    {/* Status Messages */}
                    {uploadedFile.status === 'completed' && (
                      <Alert className="mb-3">
                        <CheckCircle2 className="w-4 h-4" />
                        <AlertDescription>
                          Upload completed successfully! File processed with{' '}
                          {uploadedFile.job?.total_products || 0} products.
                        </AlertDescription>
                      </Alert>
                    )}

                    {uploadedFile.status === 'error' && (
                      <Alert variant="destructive" className="mb-3">
                        <AlertCircle className="w-4 h-4" />
                        <AlertDescription className="flex items-center justify-between">
                          <span>{uploadedFile.error}</span>
                          <Button 
                            size="sm"
                            onClick={() => retryUpload(uploadedFile.id)}
                            className="bg-black text-white hover:bg-gray-800 active:bg-gray-900 active:scale-95 transition-all duration-200 ease-in-out"
                          >
                            Retry
                          </Button>
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* File Preview and Editable Spreadsheet - Show immediately after file selection */}
                    {uploadedFile.status !== 'pending' && (
                      <div className="mt-4">
                        <div className="mb-2 space-y-2">
                          <div className="flex items-center justify-between">
                            <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              Data Preview
                            </h5>
                            {uploadedFile.status === 'validated' && (
                              <Badge variant="outline" className="text-xs">
                                Ready to upload
                              </Badge>
                            )}
                          </div>
                          
                          {/* Processing metadata display */}
                          {uploadedFile.processingMetadata && (
                            <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-3 border border-blue-200 dark:border-blue-800">
                              <div className="text-xs text-blue-800 dark:text-blue-200 space-y-1">
                                <p><strong>File Analysis:</strong></p>
                                <p>• Total rows: {uploadedFile.processingMetadata.totalRows.toLocaleString()}</p>
                                <p>• Preview showing: {uploadedFile.processingMetadata.previewRows} rows</p>
                                {uploadedFile.processingMetadata.processingBatches > 1 && (
                                  <p>• Will process in {uploadedFile.processingMetadata.processingBatches} batches</p>
                                )}
                                <p>• Estimated processing time: ~{Math.ceil(uploadedFile.processingMetadata.estimatedTime / 60)} minute(s)</p>
                                {uploadedFile.processingMetadata.isPreviewLimited && (
                                  <p className="text-blue-700 dark:text-blue-300 font-medium">
                                    ⚠️ Backend will process ALL {uploadedFile.processingMetadata.totalRows} rows, not just the preview
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                        
                        <div className="mb-2">
                          <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Preview Data {uploadedFile.processingMetadata?.isPreviewLimited ? `(${uploadedFile.processingMetadata.previewRows} of ${uploadedFile.processingMetadata.totalRows} rows)` : ''}
                          </h5>
                        </div>
                        
                        {/* Show spreadsheet if we have data */}
                        {uploadedFile.previewData && uploadedFile.previewData.length > 0 ? (
                          <div className="space-y-4">
                            <EditableSpreadsheet 
                              data={uploadedFile.previewData}
                              fileName={uploadedFile.file.name}
                              jobId={uploadedFile.job?.id}
                              onDataChange={(newData) => {
                                setUploadedFiles(prev => 
                                  prev.map(f => 
                                    f.id === uploadedFile.id 
                                      ? { ...f, previewData: newData }
                                      : f
                                  )
                                );
                              }}
                              readOnly={uploadedFile.status !== 'completed'} // Make it read-only until upload completes
                              hasHSCodes={uploadedFile.hasHSCodes || false}
                              productsWithHS={uploadedFile.hasHSCodes && uploadedFile.previewData && uploadedFile.hsMatches 
                                ? createProductsWithHSCode(uploadedFile.previewData, uploadedFile.hsMatches)
                                : undefined}
                              onHSCodeUpdate={async (productId: string, hsCode: string) => {
                                console.log('HS code update requested:', productId, hsCode);
                                // TODO: Implement HS code update API call
                              }}
                            />
                            
                            {/* Processing Actions - Only show after successful upload */}
                            {uploadedFile.status === 'completed' && uploadedFile.job && (
                              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border">
                                <h6 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                  Next Steps: Process Your Data
                                </h6>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                  <Button
                                    onClick={() => uploadedFile.job && initiateHSMatching(uploadedFile.job.id)}
                                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 shadow-sm hover:shadow-md transition-all duration-200 ease-in-out"
                                    size="lg"
                                  >
                                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                    Find HS Code
                                  </Button>
                                  <Button
                                    onClick={() => uploadedFile.job && initiateXMLGeneration(uploadedFile.job.id)}
                                    className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-3 shadow-sm hover:shadow-md transition-all duration-200 ease-in-out"
                                    disabled={uploadedFile.xmlGenerating}
                                    size="lg"
                                  >
                                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    {uploadedFile.xmlGenerating ? 'Generating XML...' : 'Generate XML File'}
                                  </Button>
                                </div>
                                
                                {/* XML Download Button */}
                                {uploadedFile.xmlDownloadUrl && (
                                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                                    <Button
                                      onClick={() => window.open(uploadedFile.xmlDownloadUrl, '_blank')}
                                      className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-3 shadow-sm hover:shadow-md transition-all duration-200 ease-in-out"
                                      size="lg"
                                    >
                                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                      Download XML File
                                    </Button>
                                  </div>
                                )}
                              </div>
                            )}
                            
                            {/* Show message when file is validated but not yet uploaded */}
                            {uploadedFile.status === 'validated' && (
                              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                                <div className="flex items-start gap-3">
                                  <svg className="w-5 h-5 mt-0.5 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  <div>
                                    <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
                                      Файл готов к загрузке
                                    </p>
                                    <p className="text-sm text-blue-700 dark:text-blue-300">
                                      Ваш файл успешно проверен. Нажмите кнопку "Загрузить файл для обработки" выше, чтобы включить сопоставление HS кодов и генерацию XML.
                                    </p>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        ) : uploadedFile.status === 'validating' ? (
                          // Loading state while parsing
                          <Card>
                            <CardContent className="p-6 text-center">
                              <div className="animate-spin w-10 h-10 mx-auto mb-3 border-4 border-primary border-t-transparent rounded-full" />
                              <p className="text-sm text-muted-foreground">
                                Loading preview...
                              </p>
                            </CardContent>
                          </Card>
                        ) : (
                          // No data available
                          <Card>
                            <CardContent className="p-6 text-center">
                              <FileSpreadsheet className="w-10 h-10 mx-auto mb-3 text-muted-foreground" />
                              <p className="text-sm text-muted-foreground">
                                No preview available
                              </p>
                              <p className="text-xs text-muted-foreground mt-2">
                                File may be empty or in an unsupported format
                              </p>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
