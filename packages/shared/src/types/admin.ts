/**
 * Admin-related type definitions
 */

export interface AdminDashboardStats {
  totalUsers: number;
  activeUsers: number;
  totalJobs: number;
  pendingJobs: number;
  successRate: number;
  avgProcessingTime: number;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down';
  services: ServiceStatus[];
  lastChecked: Date;
}

export interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  responseTime?: number;
  error?: string;
}