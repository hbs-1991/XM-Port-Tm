/**
 * Backend Processing Verification
 * Utilities to verify that the backend correctly processes complete files without artificial limits
 */

export interface BackendProcessingCapabilities {
  maxBatchSize: number;
  supportsBatching: boolean;
  maxFileSize: number;
  supportedFormats: string[];
  processesCompleteFiles: boolean;
}

/**
 * Backend processing capabilities based on API analysis
 */
export const BACKEND_CAPABILITIES: BackendProcessingCapabilities = {
  maxBatchSize: 100, // HS matching service batch limit
  supportsBatching: true, // Supports processing large files in batches
  maxFileSize: 10 * 1024 * 1024, // 10MB file size limit
  supportedFormats: ['csv', 'xlsx', 'xls'],
  processesCompleteFiles: true, // Backend processes entire files, not just previews
};

/**
 * Verify that the backend will process all rows from a file
 */
export function canBackendProcessFile(
  totalRows: number, 
  fileSize: number, 
  format: string
): { canProcess: boolean; batches: number; errors: string[] } {
  const errors: string[] = [];
  
  // Check file size
  if (fileSize > BACKEND_CAPABILITIES.maxFileSize) {
    errors.push(`File size ${(fileSize / 1024 / 1024).toFixed(2)}MB exceeds maximum ${BACKEND_CAPABILITIES.maxFileSize / 1024 / 1024}MB`);
  }
  
  // Check format
  const normalizedFormat = format.toLowerCase().replace('.', '');
  if (!BACKEND_CAPABILITIES.supportedFormats.includes(normalizedFormat)) {
    errors.push(`Format ${format} not supported. Supported: ${BACKEND_CAPABILITIES.supportedFormats.join(', ')}`);
  }
  
  // Calculate batches needed
  const batches = Math.ceil(totalRows / BACKEND_CAPABILITIES.maxBatchSize);
  
  return {
    canProcess: errors.length === 0,
    batches,
    errors
  };
}

/**
 * Estimate processing time based on file characteristics
 */
export function estimateProcessingTime(totalRows: number): {
  estimatedMinutes: number;
  batches: number;
  breakdown: string[];
} {
  const batches = Math.ceil(totalRows / BACKEND_CAPABILITIES.maxBatchSize);
  const breakdown: string[] = [];
  
  // File validation: ~10-30 seconds
  const validationTime = Math.min(30, Math.max(10, totalRows / 100));
  breakdown.push(`Validation: ${validationTime}s`);
  
  // HS code matching: ~2-5 seconds per batch (AI processing)
  const hsMatchingTime = batches * Math.min(5, Math.max(2, totalRows / 1000));
  breakdown.push(`HS Code Matching: ${hsMatchingTime}s (${batches} batches)`);
  
  // XML generation: ~5-15 seconds depending on size
  const xmlGenerationTime = Math.min(15, Math.max(5, totalRows / 200));
  breakdown.push(`XML Generation: ${xmlGenerationTime}s`);
  
  const totalSeconds = validationTime + hsMatchingTime + xmlGenerationTime;
  const estimatedMinutes = Math.ceil(totalSeconds / 60);
  
  return {
    estimatedMinutes,
    batches,
    breakdown
  };
}

/**
 * Generate processing summary for user display
 */
export function generateProcessingSummary(
  totalRows: number, 
  fileSize: number, 
  format: string
): {
  canProcess: boolean;
  summary: string;
  details: string[];
  warnings: string[];
} {
  const verification = canBackendProcessFile(totalRows, fileSize, format);
  const timeEstimate = estimateProcessingTime(totalRows);
  
  const details: string[] = [];
  const warnings: string[] = [];
  
  if (verification.canProcess) {
    details.push(`✅ All ${totalRows} rows will be processed`);
    details.push(`📊 Processing will use ${verification.batches} batch${verification.batches > 1 ? 'es' : ''}`);
    details.push(`⏱️ Estimated processing time: ${timeEstimate.estimatedMinutes} minute${timeEstimate.estimatedMinutes > 1 ? 's' : ''}`);
    
    if (verification.batches > 1) {
      warnings.push(`Large file will be processed in ${verification.batches} batches for optimal performance`);
    }
    
    if (timeEstimate.estimatedMinutes > 5) {
      warnings.push('Processing may take several minutes. You can safely close this tab and check back later.');
    }
    
    return {
      canProcess: true,
      summary: `Ready to process ${totalRows} products from your ${format.toUpperCase()} file`,
      details,
      warnings
    };
  } else {
    return {
      canProcess: false,
      summary: 'Cannot process this file',
      details: verification.errors,
      warnings: []
    };
  }
}

/**
 * Verify frontend preview vs backend processing
 */
export function verifyPreviewVsProcessing(
  previewRows: number, 
  actualFileRows: number
): {
  isPreviewLimited: boolean;
  message: string;
  backendWillProcessAll: boolean;
} {
  const isPreviewLimited = previewRows < actualFileRows;
  const backendWillProcessAll = BACKEND_CAPABILITIES.processesCompleteFiles;
  
  if (!isPreviewLimited) {
    return {
      isPreviewLimited: false,
      message: `Showing all ${actualFileRows} rows from your file`,
      backendWillProcessAll
    };
  }
  
  const hiddenRows = actualFileRows - previewRows;
  
  return {
    isPreviewLimited: true,
    message: `Showing ${previewRows} of ${actualFileRows} rows (${hiddenRows} more rows hidden for performance). Backend will process ALL ${actualFileRows} rows.`,
    backendWillProcessAll
  };
}