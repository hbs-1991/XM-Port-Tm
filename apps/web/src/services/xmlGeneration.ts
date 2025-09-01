'use client';

import { getSession } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USE_PROXY = true; // Enable proxy to avoid CORS issues with WSL

interface XMLGenerationRequest {
  job_id: string;
  country_schema?: 'TKM';
  include_metadata?: boolean;
  validate_output?: boolean;
}

interface XMLGenerationResponse {
  success: boolean;
  job_id: string;
  xml_file_name: string;
  download_url: string;
  country_schema: string;
  generated_at: string;
  file_size: number;
  summary?: any;
  validation_errors?: string[];
  error_message?: string;
}

interface XMLDownloadResponse {
  success: boolean;
  job_id: string;
  download_url: string;
  file_name: string;
  file_size: number;
  expires_at?: string;
  content_type: string;
  error_message?: string;
}

interface XMLStatusResponse {
  job_id: string;
  xml_generation_status: string;
  xml_available: boolean;
  xml_generated_at?: string;
  xml_file_size?: number;
  country_schema: string;
  total_products: number;
  successful_matches: number;
  average_confidence?: number;
  processing_status: string;
  error_message?: string;
}

class XMLGenerationService {
  private async fetchWithAuth(url: string, options: RequestInit = {}) {
    const session = await getSession();
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
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

  async generateXML(
    jobId: string, 
    request?: Omit<XMLGenerationRequest, 'job_id'>
  ): Promise<XMLGenerationResponse> {
    const payload: XMLGenerationRequest = {
      job_id: jobId,
      country_schema: request?.country_schema || 'TKM',
      include_metadata: request?.include_metadata ?? true,
      validate_output: request?.validate_output ?? true
    };

    const response = await this.fetchWithAuth(
      `/api/v1/processing/${jobId}/generate-xml`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );

    return response.json();
  }

  async getXMLDownloadInfo(jobId: string): Promise<XMLDownloadResponse> {
    const response = await this.fetchWithAuth(
      `/api/v1/processing/${jobId}/xml-download`,
      {
        method: 'GET',
      }
    );

    return response.json();
  }

  async getXMLStatus(jobId: string): Promise<XMLStatusResponse> {
    const response = await this.fetchWithAuth(
      `/api/v1/processing/${jobId}/xml-status`,
      {
        method: 'GET',
      }
    );

    return response.json();
  }

  async downloadXMLFile(jobId: string): Promise<Blob> {
    const downloadInfo = await this.getXMLDownloadInfo(jobId);
    
    // Download the file using the provided URL
    const response = await fetch(downloadInfo.download_url);
    
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.statusText}`);
    }
    
    return response.blob();
  }
}

// Create singleton instance
const xmlGenerationService = new XMLGenerationService();

// Export individual functions for easier use
export const generateXML = xmlGenerationService.generateXML.bind(xmlGenerationService);
export const getXMLDownloadInfo = xmlGenerationService.getXMLDownloadInfo.bind(xmlGenerationService);
export const getXMLStatus = xmlGenerationService.getXMLStatus.bind(xmlGenerationService);
export const downloadXMLFile = xmlGenerationService.downloadXMLFile.bind(xmlGenerationService);

export default xmlGenerationService;