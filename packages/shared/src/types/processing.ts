/**
 * File processing related type definitions
 */

export interface ProcessingJob {
  id: string;
  userId?: string;
  status: ProcessingStatus;
  input_file_name: string;
  input_file_url?: string;
  input_file_size: number;
  output_xml_url?: string;
  xml_generation_status?: string;
  credits_used: number;
  processing_time_ms?: number;
  total_products: number;
  successful_matches: number;
  average_confidence?: number;
  country_schema: string;
  error_message?: string;
  has_xml_output?: boolean;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export enum ProcessingStatus {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  COMPLETED_WITH_ERRORS = 'COMPLETED_WITH_ERRORS',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED'
}

export interface ProductMatch {
  id: string;
  jobId: string;
  productDescription: string;
  quantity: number;
  unitOfMeasure: string;
  value: number;
  originCountry: string;
  matchedHsCode: string;
  confidenceScore: number;
  alternativeHsCodes: string[];
  requiresManualReview: boolean;
  userConfirmed: boolean;
  createdAt: Date;
}

export interface HSCode {
  code: string;
  description: string;
  chapter: string;
  section: string;
  country: string;
  isActive: boolean;
  updatedAt: Date;
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