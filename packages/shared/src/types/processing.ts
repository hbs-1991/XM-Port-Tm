/**
 * File processing related type definitions
 */

export interface ProcessingJob {
  id: string;
  userId: string;
  status: ProcessingStatus;
  inputFileName: string;
  inputFileUrl: string;
  inputFileSize: number;
  outputXmlUrl?: string;
  creditsUsed: number;
  processingTimeMs?: number;
  totalProducts: number;
  successfulMatches: number;
  averageConfidence: number;
  countrySchema: string;
  errorMessage?: string;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
}

export enum ProcessingStatus {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
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