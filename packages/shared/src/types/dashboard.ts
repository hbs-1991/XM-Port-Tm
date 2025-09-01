/**
 * Dashboard-specific type definitions
 */

export interface UserStatistics {
  totalJobs: number;
  successRate: number;
  averageConfidence: number;
  monthlyUsage: MonthlyUsage;
  creditBalance: CreditBalance;
  processingStats: ProcessingStats;
}

export interface MonthlyUsage {
  creditsUsed: number;
  jobsCompleted: number;
  filesProcessed: number;
  averageProcessingTime: number;
  month: string;
  year: number;
}

export interface CreditBalance {
  remaining: number;
  total: number;
  usedThisMonth: number;
  percentageUsed: number;
  subscriptionTier: string;
}

export interface ProcessingStats {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  successRate: number;
  averageConfidence: number;
  totalProducts: number;
  successfulMatches: number;
}

export interface UsageAnalytics {
  dailyUsage: DailyUsageData[];
  monthlyTrends: MonthlyTrendData[];
  topProcessingHours: HourlyUsageData[];
  performanceMetrics: PerformanceMetric[];
}

export interface DailyUsageData {
  date: string;
  creditsUsed: number;
  jobsCompleted: number;
  averageConfidence: number;
}

export interface MonthlyTrendData {
  month: string;
  year: number;
  creditsUsed: number;
  jobsCompleted: number;
  successRate: number;
}

export interface HourlyUsageData {
  hour: number;
  jobCount: number;
  averageProcessingTime: number;
}

export interface PerformanceMetric {
  metric: string;
  value: number;
  trend: 'up' | 'down' | 'stable';
  percentageChange: number;
}