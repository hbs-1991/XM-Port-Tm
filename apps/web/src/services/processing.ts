'use client';

import { ProcessingJob } from '@xm-port/shared/types';

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

interface UploadResponse extends ProcessingJob {
  previewData?: any[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ProcessingService {
  private async fetchWithAuth(url: string, options: RequestInit = {}) {
    // TODO: Add authentication headers when auth is implemented
    const headers = {
      ...options.headers,
      // 'Authorization': `Bearer ${token}`,
    };

    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Network error' }));
      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    return response;
  }

  async uploadFile({ 
    file, 
    fileId, 
    countrySchema, 
    onProgress 
  }: UploadFileParams): Promise<UploadResponse> {
    return new Promise((resolve, reject) => {
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
          } else {
            const errorResponse = JSON.parse(xhr.responseText);
            reject(new Error(errorResponse.message || `Upload failed with status ${xhr.status}`));
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
      xhr.open('POST', `${API_BASE_URL}/api/v1/processing/upload`);
      
      // TODO: Add auth header when implemented
      // xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      
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

  async validateFile(file: File): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
    previewData?: any[];
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.fetchWithAuth('/api/v1/processing/validate', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();
    return data;
  }
}

// Create singleton instance
const processingService = new ProcessingService();

// Export individual functions for easier use with React Query
export const uploadFile = processingService.uploadFile.bind(processingService);
export const getProcessingJob = processingService.getProcessingJob.bind(processingService);
export const getUserJobs = processingService.getUserJobs.bind(processingService);
export const cancelProcessingJob = processingService.cancelProcessingJob.bind(processingService);
export const retryProcessingJob = processingService.retryProcessingJob.bind(processingService);
export const downloadResults = processingService.downloadResults.bind(processingService);
export const validateFile = processingService.validateFile.bind(processingService);

export default processingService;