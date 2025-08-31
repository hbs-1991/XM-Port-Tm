'use client';

import { getSession } from 'next-auth/react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USE_PROXY = true; // Enable proxy to avoid CORS issues with WSL

interface HSMatchRequest {
  product_description: string;
  country?: string;
  include_alternatives?: boolean;
  confidence_threshold?: number;
}

interface HSBatchMatchRequest {
  products: HSMatchRequest[];
  country?: string;
}

interface HSMatch {
  hs_code: string;
  code_description: string;
  confidence: number;
  chapter: string;
  section: string;
}

interface HSMatchResult {
  primary_match: HSMatch;
  alternative_matches: HSMatch[];
  product_description: string;
}

interface HSMatchResponse {
  success: boolean;
  data: HSMatchResult;
  processing_time_ms: number;
}

interface HSBatchMatchResponse {
  success: boolean;
  data: HSMatchResult[];
  processing_time_ms: number;
  total_processed: number;
  successful_matches: number;
}

class HSMatchingService {
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

  async matchSingleProduct(request: HSMatchRequest): Promise<HSMatchResult> {
    const response = await this.fetchWithAuth('/api/v1/hs-codes/match', {
      method: 'POST',
      body: JSON.stringify(request),
    });

    const data: HSMatchResponse = await response.json();
    return data.data;
  }

  async matchBatchProducts(request: HSBatchMatchRequest): Promise<HSMatchResult[]> {
    const response = await this.fetchWithAuth('/api/v1/hs-codes/batch-match', {
      method: 'POST',
      body: JSON.stringify(request),
    });

    const data: HSBatchMatchResponse = await response.json();
    return data.data;
  }

  async searchHSCodes(query: string, country?: string, limit: number = 10): Promise<any> {
    const params = new URLSearchParams({
      query,
      limit: limit.toString(),
    });
    
    if (country) {
      params.append('country', country);
    }

    const response = await this.fetchWithAuth(`/api/v1/hs-codes/search?${params}`, {
      method: 'GET',
    });

    return response.json();
  }

  async getHealthStatus(): Promise<any> {
    const response = await this.fetchWithAuth('/api/v1/hs-codes/health', {
      method: 'GET',
    });

    return response.json();
  }

  async getCacheStats(): Promise<any> {
    const response = await this.fetchWithAuth('/api/v1/hs-codes/cache/stats', {
      method: 'GET',
    });

    return response.json();
  }
}

// Create singleton instance
const hsMatchingService = new HSMatchingService();

// Export individual functions for easier use
export const matchSingleProduct = hsMatchingService.matchSingleProduct.bind(hsMatchingService);
export const matchBatchProducts = hsMatchingService.matchBatchProducts.bind(hsMatchingService);
export const searchHSCodes = hsMatchingService.searchHSCodes.bind(hsMatchingService);
export const getHealthStatus = hsMatchingService.getHealthStatus.bind(hsMatchingService);
export const getCacheStats = hsMatchingService.getCacheStats.bind(hsMatchingService);

export default hsMatchingService;