/**
 * File preview configuration for the XM-PORT application
 * Controls how many rows to show in previews based on file characteristics
 */

export interface PreviewConfig {
  maxPreviewRows: number;
  performanceThreshold: number; // File size threshold in bytes
  readChunkSize: number; // Maximum bytes to read for preview
}

export interface FilePreviewOptions {
  fileSize: number;
  isValidated?: boolean;
  userPreference?: number;
}

/**
 * Default preview configuration
 */
export const DEFAULT_PREVIEW_CONFIG: PreviewConfig = {
  maxPreviewRows: 100, // Default maximum preview rows
  performanceThreshold: 1024 * 1024, // 1MB threshold
  readChunkSize: 2 * 1024 * 1024, // Read up to 2MB for preview
};

/**
 * Calculate optimal preview size based on file characteristics
 */
export function getOptimalPreviewSize(options: FilePreviewOptions): number {
  const { fileSize, isValidated = false, userPreference } = options;
  
  // User preference takes priority
  if (userPreference && userPreference > 0) {
    return Math.min(userPreference, 500); // Cap at 500 rows for performance
  }
  
  // Performance-based sizing
  if (fileSize > 10 * 1024 * 1024) { // Files larger than 10MB
    return 25;
  } else if (fileSize > 5 * 1024 * 1024) { // Files larger than 5MB
    return 50;
  } else if (fileSize > DEFAULT_PREVIEW_CONFIG.performanceThreshold) { // Files larger than 1MB
    return 75;
  } else {
    return DEFAULT_PREVIEW_CONFIG.maxPreviewRows; // Small files get full preview
  }
}

/**
 * Get page size for pagination based on dataset size
 */
export function getOptimalPageSize(dataLength: number): number {
  if (dataLength <= 50) return dataLength; // Show all if small dataset
  if (dataLength <= 200) return 25; // Medium page size for medium datasets
  return 20; // Standard page size for large datasets
}

/**
 * Determine if a file should use lazy loading
 */
export function shouldUseLazyLoading(dataLength: number): boolean {
  return dataLength > 100;
}

/**
 * Get read chunk size based on file characteristics
 */
export function getReadChunkSize(fileSize: number): number {
  if (fileSize > 10 * 1024 * 1024) { // Very large files (>10MB)
    return 1 * 1024 * 1024; // Read 1MB chunks
  } else if (fileSize > 5 * 1024 * 1024) { // Large files (>5MB)
    return 2 * 1024 * 1024; // Read 2MB chunks
  } else {
    return fileSize; // Read entire small files
  }
}

/**
 * User preference storage keys
 */
export const PREVIEW_STORAGE_KEYS = {
  MAX_ROWS: 'xm-port-preview-max-rows',
  LAZY_LOADING: 'xm-port-preview-lazy-loading',
} as const;

/**
 * Get user preview preferences from localStorage
 */
export function getUserPreviewPreferences(): {
  maxRows?: number;
  lazyLoading?: boolean;
} {
  try {
    const maxRows = localStorage.getItem(PREVIEW_STORAGE_KEYS.MAX_ROWS);
    const lazyLoading = localStorage.getItem(PREVIEW_STORAGE_KEYS.LAZY_LOADING);
    
    return {
      maxRows: maxRows ? parseInt(maxRows, 10) : undefined,
      lazyLoading: lazyLoading ? JSON.parse(lazyLoading) : undefined,
    };
  } catch {
    return {};
  }
}

/**
 * Save user preview preferences to localStorage
 */
export function saveUserPreviewPreferences(preferences: {
  maxRows?: number;
  lazyLoading?: boolean;
}): void {
  try {
    if (preferences.maxRows !== undefined) {
      localStorage.setItem(PREVIEW_STORAGE_KEYS.MAX_ROWS, preferences.maxRows.toString());
    }
    if (preferences.lazyLoading !== undefined) {
      localStorage.setItem(PREVIEW_STORAGE_KEYS.LAZY_LOADING, JSON.stringify(preferences.lazyLoading));
    }
  } catch {
    // Ignore localStorage errors
  }
}

/**
 * Preview performance metrics
 */
export interface PreviewMetrics {
  parseTime: number;
  renderTime: number;
  memoryUsage?: number;
  rowsProcessed: number;
}

/**
 * Track preview performance for optimization
 */
export class PreviewPerformanceTracker {
  private metrics: Map<string, PreviewMetrics[]> = new Map();
  
  startTracking(fileId: string): { parseStart: number; renderStart: number } {
    const parseStart = performance.now();
    return {
      parseStart,
      renderStart: parseStart,
    };
  }
  
  endTracking(
    fileId: string,
    timings: { parseStart: number; renderStart: number },
    rowsProcessed: number
  ): PreviewMetrics {
    const now = performance.now();
    const metrics: PreviewMetrics = {
      parseTime: now - timings.parseStart,
      renderTime: now - timings.renderStart,
      rowsProcessed,
      memoryUsage: this.getMemoryUsage(),
    };
    
    const fileMetrics = this.metrics.get(fileId) || [];
    fileMetrics.push(metrics);
    this.metrics.set(fileId, fileMetrics);
    
    return metrics;
  }
  
  private getMemoryUsage(): number | undefined {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return undefined;
  }
  
  getAverageMetrics(fileId: string): PreviewMetrics | null {
    const fileMetrics = this.metrics.get(fileId);
    if (!fileMetrics || fileMetrics.length === 0) return null;
    
    const avg = fileMetrics.reduce(
      (acc, metric) => ({
        parseTime: acc.parseTime + metric.parseTime,
        renderTime: acc.renderTime + metric.renderTime,
        memoryUsage: (acc.memoryUsage || 0) + (metric.memoryUsage || 0),
        rowsProcessed: acc.rowsProcessed + metric.rowsProcessed,
      }),
      { parseTime: 0, renderTime: 0, memoryUsage: 0, rowsProcessed: 0 }
    );
    
    const count = fileMetrics.length;
    return {
      parseTime: avg.parseTime / count,
      renderTime: avg.renderTime / count,
      memoryUsage: avg.memoryUsage ? avg.memoryUsage / count : undefined,
      rowsProcessed: avg.rowsProcessed / count,
    };
  }
  
  shouldReducePreview(fileId: string): boolean {
    const avgMetrics = this.getAverageMetrics(fileId);
    if (!avgMetrics) return false;
    
    // Reduce preview if parsing takes too long or memory usage is high
    return (
      avgMetrics.parseTime > 1000 || // More than 1 second to parse
      Boolean(avgMetrics.memoryUsage && avgMetrics.memoryUsage > 50 * 1024 * 1024) // More than 50MB memory
    );
  }
}

/**
 * Global performance tracker instance
 */
export const previewPerformanceTracker = new PreviewPerformanceTracker();