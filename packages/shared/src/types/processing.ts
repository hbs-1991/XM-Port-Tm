/**
 * File processing related type definitions
 */

export interface ProcessingJob {
  id: string;
  userId: string;
  filename: string;
  fileSize: number;
  status: ProcessingStatus;
  progress: number;
  createdAt: Date;
  completedAt?: Date;
  results?: ProcessingResults;
  error?: string;
}

export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface ProcessingResults {
  extractedData: Record<string, any>;
  hsCodeMatches: HSCodeMatch[];
  xmlOutput?: string;
}

export interface HSCodeMatch {
  code: string;
  description: string;
  confidence: number;
  category: string;
}

export interface FileUploadRequest {
  file: File;
  processingOptions?: ProcessingOptions;
}

export interface ProcessingOptions {
  extractionMode: 'basic' | 'advanced';
  validateHsCodes: boolean;
  generateXml: boolean;
}