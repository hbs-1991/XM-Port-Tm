'use client';

import { ProcessingJob } from '@xm-port/shared';

interface UploadFileParams {
  file: File;
  fileId: string;
  countrySchema: string;
  onProgress?: (progress: number) => void;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

interface UploadResponse {
  job_id: string;
  file_name: string;
  file_size: number;
  status: string;
  message: string;
  validation_results?: any;
  previewData?: any[];
  // Optional fields that may be returned
  credits_used?: number;
  total_products?: number;
  successful_matches?: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USE_PROXY = true; // Enable proxy to avoid CORS issues with WSL

class ProcessingService {
  private async fetchWithAuth(url: string, options: RequestInit = {}) {
    // Get NextAuth session token
    const { getSession } = await import('next-auth/react');
    const session = await getSession();
    
    const headers = {
      ...options.headers,
    };
    
    // Add authorization header if session exists
    if (session?.accessToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${session.accessToken}`;
    }

    const baseUrl = USE_PROXY ? '/api/proxy' : API_BASE_URL;
    const response = await fetch(`${baseUrl}${url}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Network error' }));
      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    return response;
  }

  async validateFile(file: File): Promise<{
    valid: boolean;
    errors: any[];
    warnings: string[];
    total_rows: number;
    valid_rows: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.fetchWithAuth('/api/v1/processing/validate', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Validation failed: ${error}`);
    }

    return response.json();
  }

  async uploadFile({ 
    file, 
    fileId, 
    countrySchema, 
    onProgress 
  }: UploadFileParams): Promise<UploadResponse> {
    return this.uploadFileWithRetry({ file, fileId, countrySchema, onProgress }, 3);
  }

  private async uploadFileWithRetry(
    params: UploadFileParams, 
    maxRetries: number,
    currentAttempt: number = 1
  ): Promise<UploadResponse> {
    // Get auth token first
    const { getSession } = await import('next-auth/react');
    const session = await getSession();
    
    return new Promise((resolve, reject) => {
      const { file, fileId, countrySchema, onProgress } = params;
      const formData = new FormData();
      formData.append('file', file);
      formData.append('country_schema', countrySchema);

      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = (event.loaded / event.total) * 100;
          onProgress?.(progress);
        }
      });

      xhr.addEventListener('load', async () => {
        try {
          if (xhr.status === 200 || xhr.status === 201) {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } else if (xhr.status === 409 && currentAttempt < maxRetries) {
            // Handle 409 Conflict with exponential backoff retry
            const errorResponse = JSON.parse(xhr.responseText);
            const isRetryable = errorResponse.detail?.error === 'credit_reservation_conflict' || 
                              errorResponse.detail?.retry_suggested;
            
            if (isRetryable) {
              const delay = Math.min(1000 * Math.pow(2, currentAttempt - 1), 5000); // Max 5s delay
              console.log(`Upload conflict detected, retrying in ${delay}ms (attempt ${currentAttempt + 1}/${maxRetries})`);
              
              setTimeout(() => {
                this.uploadFileWithRetry(params, maxRetries, currentAttempt + 1)
                  .then(resolve)
                  .catch(reject);
              }, delay);
              return;
            }
            
            // Not retryable 409 error
            const errorMessage = errorResponse.detail?.message || errorResponse.message || `Upload failed with status ${xhr.status}`;
            reject(new Error(errorMessage));
          } else {
            // Parse error response for better error messages
            try {
              const errorResponse = JSON.parse(xhr.responseText);
              const errorMessage = errorResponse.detail?.message || 
                                 errorResponse.message || 
                                 `Upload failed with status ${xhr.status}`;
              reject(new Error(errorMessage));
            } catch {
              reject(new Error(`Upload failed with status ${xhr.status}`));
            }
          }
        } catch (error) {
          reject(new Error('Failed to parse server response'));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload was cancelled'));
      });

      xhr.addEventListener('timeout', () => {
        reject(new Error('Upload timed out'));
      });

      xhr.timeout = 300000; // 5 minutes timeout
      const baseUrl = USE_PROXY ? '/api/proxy' : API_BASE_URL;
      xhr.open('POST', `${baseUrl}/api/v1/processing/upload`);
      
      // Add auth header if available
      if (session?.accessToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${session.accessToken}`);
      }
      
      xhr.send(formData);
    });
  }

  async getProcessingJob(jobId: string): Promise<ProcessingJob> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}`);
    const data = await response.json();
    return data;
  }

  async getUserJobs(limit = 10, offset = 0): Promise<{ jobs: ProcessingJob[]; total: number }> {
    const response = await this.fetchWithAuth(
      `/api/v1/processing/jobs?limit=${limit}&offset=${offset}`
    );
    const data = await response.json();
    return data;
  }

  async cancelProcessingJob(jobId: string): Promise<void> {
    await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
  }

  async retryProcessingJob(jobId: string): Promise<ProcessingJob> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/retry`, {
      method: 'POST',
    });
    const data = await response.json();
    return data;
  }

  async downloadResults(jobId: string): Promise<Blob> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/download`);
    return response.blob();
  }

  async getJobProducts(jobId: string): Promise<{
    job_id: string;
    status: string;
    products: Array<{
      id: string;
      product_description: string;
      quantity: number;
      unit: string;
      value: number;
      origin_country: string;
      unit_price: number;
      hs_code: string;
      confidence_score: number;
      confidence_level: 'High' | 'Medium' | 'Low';
      alternative_hs_codes: string[];
      requires_manual_review: boolean;
      user_confirmed: boolean;
      vector_store_reasoning?: string;
    }>;
    total_products: number;
    high_confidence_count: number;
    requires_review_count: number;
  }> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/products`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch job products: ${response.status}`);
    }

    return await response.json();
  }

  async updateHSCode(jobId: string, productId: string, hsCode: string): Promise<{
    success: boolean;
    message: string;
    product_id: string;
    new_hs_code: string;
  }> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/products/${productId}/hs-code`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ hs_code: hsCode }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to update HS code: ${response.status}`);
    }

    return await response.json();
  }

  async processFileWithHSMatching({ 
    file, 
    fileId, 
    countrySchema, 
    onProgress 
  }: UploadFileParams): Promise<{
    success: boolean;
    job_id: string;
    products_processed: number;
    processing_errors: string[];
    credits_used: number;
    processing_time_ms: number;
    hs_matching_summary: any;
    validation_summary: {
      total_rows: number;
      valid_rows: number;
      warnings: string[];
    };
  }> {
    return this.processFileWithHSMatchingWithRetry({ file, fileId, countrySchema, onProgress }, 3);
  }

  private async processFileWithHSMatchingWithRetry(
    params: UploadFileParams, 
    maxRetries: number,
    currentAttempt: number = 1
  ): Promise<any> {
    // Get auth token first
    const { getSession } = await import('next-auth/react');
    const session = await getSession();
    
    return new Promise((resolve, reject) => {
      const { file, fileId, countrySchema, onProgress } = params;
      const formData = new FormData();
      formData.append('file', file);
      formData.append('country_schema', countrySchema);

      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = (event.loaded / event.total) * 50; // First 50% is upload
          onProgress?.(progress);
        }
      });

      xhr.addEventListener('load', async () => {
        try {
          if (xhr.status === 200 || xhr.status === 201) {
            const response = JSON.parse(xhr.responseText);
            onProgress?.(100); // Complete
            resolve(response);
          } else if (xhr.status === 409 && currentAttempt < maxRetries) {
            // Handle 409 Conflict with exponential backoff retry
            const errorResponse = JSON.parse(xhr.responseText);
            const isRetryable = errorResponse.detail?.error === 'credit_reservation_conflict' || 
                              errorResponse.detail?.retry_suggested;
            
            if (isRetryable) {
              const delay = Math.min(1000 * Math.pow(2, currentAttempt - 1), 5000); // Max 5s delay
              console.log(`Processing conflict detected, retrying in ${delay}ms (attempt ${currentAttempt + 1}/${maxRetries})`);
              
              setTimeout(() => {
                this.processFileWithHSMatchingWithRetry(params, maxRetries, currentAttempt + 1)
                  .then(resolve)
                  .catch(reject);
              }, delay);
              return;
            }
            
            // Not retryable 409 error
            const errorMessage = errorResponse.detail?.message || errorResponse.message || `Processing failed with status ${xhr.status}`;
            reject(new Error(errorMessage));
          } else {
            // Parse error response for better error messages
            try {
              const errorResponse = JSON.parse(xhr.responseText);
              const errorMessage = errorResponse.detail?.message || 
                                 errorResponse.message || 
                                 `Processing failed with status ${xhr.status}`;
              reject(new Error(errorMessage));
            } catch {
              reject(new Error(`Processing failed with status ${xhr.status}`));
            }
          }
        } catch (error) {
          reject(new Error('Failed to parse server response'));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during processing'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Processing was cancelled'));
      });

      xhr.addEventListener('timeout', () => {
        reject(new Error('Processing timed out'));
      });

      xhr.timeout = 300000; // 5 minutes timeout
      const baseUrl = USE_PROXY ? '/api/proxy' : API_BASE_URL;
      xhr.open('POST', `${baseUrl}/api/v1/processing/process-with-hs-matching`);
      
      // Add auth header if available
      if (session?.accessToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${session.accessToken}`);
      }
      
      xhr.send(formData);
    });
  }

  async completeJobAfterHSMatching(
    jobId: string,
    hsMatches: Array<{
      product_description: string;
      matched_hs_code: string;
      confidence_score: number;
      code_description: string;
      chapter: string;
      section: string;
      processing_time_ms: number;
      // The following fields are present on the objects we build in FileUpload
      quantity: number;
      unit_of_measure: string;
      value?: number;
      unit_price?: number;
      origin_country: string;
      packages_count?: number;
      packages_part?: string;
      packaging_kind_code?: string;
      packaging_kind_name?: string;
      gross_weight?: number;
      net_weight?: number;
      supplementary_quantity?: number;
      supplementary_uom_code?: string;
      supplementary_uom_name?: string;
    }>,
    processingErrors: string[] = []
  ): Promise<{
    success: boolean;
    job_id: string;
    status: string;
    total_products: number;
    successful_matches: number;
    average_confidence?: number;
    processing_time_ms: number;
    message: string;
  }> {
    // Build payload once
    const payload = {
      hs_matches: hsMatches.map(match => ({
        product_description: match.product_description,
        matched_hs_code: match.matched_hs_code,
        confidence_score: match.confidence_score,
        code_description: match.code_description,
        chapter: match.chapter,
        section: match.section,
        processing_time_ms: match.processing_time_ms,
        // Include required ProductMatch fields
        quantity: match.quantity,
        unit_of_measure: match.unit_of_measure,
        value: match.value,
        unit_price: match.unit_price,
        origin_country: match.origin_country,
        // Optional detailed fields
        packages_count: match.packages_count,
        packages_part: match.packages_part,
        packaging_kind_code: match.packaging_kind_code,
        packaging_kind_name: match.packaging_kind_name,
        gross_weight: match.gross_weight,
        net_weight: match.net_weight,
        supplementary_quantity: match.supplementary_quantity,
        supplementary_uom_code: match.supplementary_uom_code,
        supplementary_uom_name: match.supplementary_uom_name,
      })),
      processing_errors: processingErrors,
    };

    // Use a specialized request to gracefully handle non-200 responses and surface backend messages
    const { getSession } = await import('next-auth/react');
    const session = await getSession();
    const baseUrl = USE_PROXY ? '/api/proxy' : API_BASE_URL;

    const response = await fetch(`${baseUrl}/api/v1/processing/jobs/${jobId}/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
      },
      body: JSON.stringify(payload),
    });

    // Always try to parse JSON for clearer errors
    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const backendMessage = (data && (data.detail?.message || data.detail || data.message)) || undefined;
      throw new Error(backendMessage || `Failed to complete job: HTTP ${response.status}`);
    }

    // data should conform to JobCompletionResponse now
    return data as any;
  }
}

// Create singleton instance
const processingService = new ProcessingService();

// Export individual functions for easier use with React Query
export const uploadFile = processingService.uploadFile.bind(processingService);
export const processFileWithHSMatching = processingService.processFileWithHSMatching.bind(processingService);
export const getProcessingJob = processingService.getProcessingJob.bind(processingService);
export const getUserJobs = processingService.getUserJobs.bind(processingService);
export const cancelProcessingJob = processingService.cancelProcessingJob.bind(processingService);
export const retryProcessingJob = processingService.retryProcessingJob.bind(processingService);
export const downloadResults = processingService.downloadResults.bind(processingService);
export const validateFile = processingService.validateFile.bind(processingService);
export const getJobProducts = processingService.getJobProducts.bind(processingService);
export const updateHSCode = processingService.updateHSCode.bind(processingService);
export const completeJobAfterHSMatching = processingService.completeJobAfterHSMatching.bind(processingService);

export default processingService;
