'use client';

export interface JobData {
  job_id: string;
  data: any[];
  metadata: {
    job_id: string;
    file_name: string;
    total_rows: number;
    status: string;
    created_at: string;
  };
}

export interface UpdateDataResponse {
  message: string;
  job_id: string;
  rows_updated: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USE_PROXY = true; // Enable proxy to avoid CORS issues with WSL

class DataEditingService {
  private async fetchWithAuth(url: string, options: RequestInit = {}) {
    // TODO: Add authentication headers when auth is implemented
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
      // 'Authorization': `Bearer ${token}`,
    };

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

  /**
   * Get processing job data for editing
   */
  async getJobData(jobId: string): Promise<JobData> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/data`);
    return response.json();
  }

  /**
   * Update processing job data with edited values
   */
  async updateJobData(jobId: string, data: any[]): Promise<UpdateDataResponse> {
    const response = await this.fetchWithAuth(`/api/v1/processing/jobs/${jobId}/data`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
    return response.json();
  }
}

// Create singleton instance
const dataEditingService = new DataEditingService();

// Export individual functions for easier use with React Query
export const getJobData = dataEditingService.getJobData.bind(dataEditingService);
export const updateJobData = dataEditingService.updateJobData.bind(dataEditingService);

export default dataEditingService;