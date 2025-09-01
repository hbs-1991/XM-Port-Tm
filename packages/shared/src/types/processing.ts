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
  jobId?: string;
  product_description: string;
  quantity: number;
  unit_of_measure: string;
  value: number;
  origin_country: string;
  matched_hs_code: string;
  confidence_score: number;
  alternative_hs_codes: string[];
  vector_store_reasoning?: string;
  requires_manual_review: boolean;
  user_confirmed: boolean;
  created_at: string;
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

export interface JobDetailsStatistics {
  total_matches: number;
  high_confidence_matches: number;
  manual_review_required: number;
  user_confirmed: number;
  success_rate: number;
}

export interface JobDetailsResponse {
  job: ProcessingJob;
  product_matches: ProductMatch[];
  statistics: JobDetailsStatistics;
}

export type ConfidenceLevel = 'High' | 'Medium' | 'Low';

export interface ProductWithHSCode {
  id: string;
  product_description: string;
  quantity: number;
  unit: string;
  value: number;
  origin_country: string;
  unit_price: number;
  hs_code: string;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  alternative_hs_codes: string[];
  requires_manual_review: boolean;
  user_confirmed: boolean;
  vector_store_reasoning?: string;
}

export interface JobProductsResponse {
  job_id: string;
  status: string;
  products: ProductWithHSCode[];
  total_products: number;
  high_confidence_count: number;
  requires_review_count: number;
}