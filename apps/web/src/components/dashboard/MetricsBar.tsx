/**
 * MetricsBar component showing key performance indicators with mobile-first responsive design
 * Phase 1 UX improvements: Reduced cognitive load, consistent visual design, better mobile experience
 */
'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Progress } from '@/components/shared/ui/progress'
import { Button } from '@/components/shared/ui/button'
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  CreditCard, 
  FileText, 
  Target, 
  Brain, 
  Calendar,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { clsx } from 'clsx'

export interface MetricsData {
  creditBalance: {
    remaining: number;
    total: number;
    percentage: number;
    trend: 'up' | 'down' | 'stable';
  };
  totalJobs: {
    count: number;
    trend: 'up' | 'down' | 'stable';
    percentageChange: number;
  };
  successRate: {
    percentage: number;
    trend: 'up' | 'down' | 'stable';
  };
  averageConfidence: {
    score: number;
    trend: 'up' | 'down' | 'stable';
  };
  monthlyUsage: {
    creditsUsed: number;
    jobsCompleted: number;
    month: string;
    percentageChange: number;
  };
}

interface MetricsBarProps {
  data?: MetricsData;
  loading?: boolean;
  className?: string;
}

interface MetricCardProps {
  title: string;
  value: string;
  description: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: number;
  variant: 'primary' | 'success' | 'warning' | 'neutral';
  progressValue?: number;
  showProgress?: boolean;
  priority: 'essential' | 'detailed';
}

// Unified design system colors
const getVariantStyles = (variant: 'primary' | 'success' | 'warning' | 'neutral'): string => {
  const variants = {
    primary: 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100',
    success: 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100', 
    warning: 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100',
    neutral: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'
  };
  return variants[variant];
};

// Smart color assignment based on performance thresholds
const getCreditBalanceVariant = (percentage: number): 'success' | 'warning' | 'neutral' => {
  if (percentage > 50) return 'success';
  if (percentage >= 25) return 'warning';
  return 'neutral';
};

const getSuccessRateVariant = (percentage: number): 'success' | 'warning' | 'neutral' => {
  if (percentage > 95) return 'success';
  if (percentage >= 90) return 'warning';
  return 'neutral';
};

const getConfidenceVariant = (score: number): 'success' | 'warning' | 'neutral' => {
  if (score > 90) return 'success';
  if (score >= 85) return 'warning';
  return 'neutral';
};

const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
  switch (trend) {
    case 'up':
      return <TrendingUp className="h-3 w-3 text-green-600" />;
    case 'down':
      return <TrendingDown className="h-3 w-3 text-red-600" />;
    case 'stable':
    default:
      return <Minus className="h-3 w-3 text-gray-500" />;
  }
};

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  description,
  icon,
  trend,
  trendValue,
  variant,
  progressValue,
  showProgress = false,
  priority
}) => {
  return (
    <Card className={clsx(
      'transition-all duration-200 hover:shadow-md border',
      getVariantStyles(variant),
      priority === 'essential' ? 'ring-1 ring-blue-200' : ''
    )}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          {title}
        </CardTitle>
        <div className="h-4 w-4 opacity-70">
          {icon}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-xl font-bold mb-1" aria-label={`${title}: ${value}`}>
          {value}
        </div>
        <CardDescription className="text-xs mb-2 leading-relaxed">
          {description}
        </CardDescription>
        
        {showProgress && progressValue !== undefined && (
          <div className="mb-2">
            <Progress 
              value={progressValue} 
              className="h-1.5"
              aria-label={`${title} progress: ${progressValue}%`}
            />
          </div>
        )}
        
        {trend && (
          <div className="flex items-center space-x-1" role="status" aria-live="polite">
            {getTrendIcon(trend)}
            <span className="text-xs text-gray-600">
              {trend === 'stable' ? 'Stable' : 
               trend === 'up' ? 'Trending up' : 'Trending down'}
              {trendValue !== undefined && trend !== 'stable' && 
                ` (${Math.abs(trendValue)}%)`}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export const MetricsBar: React.FC<MetricsBarProps> = ({
  data,
  loading = false,
  className = ''
}) => {
  const [showDetailedMetrics, setShowDetailedMetrics] = useState(false);

  if (loading || !data) {
    return <MetricsBarSkeleton className={className} />;
  }

  // Essential metrics for mobile (always visible)
  const essentialMetrics = [
    {
      title: 'Credits',
      value: `${data.creditBalance.remaining.toLocaleString()}`,
      description: `${data.creditBalance.percentage.toFixed(0)}% remaining`,
      icon: <CreditCard className="h-4 w-4" />,
      trend: data.creditBalance.trend,
      trendValue: undefined,
      variant: getCreditBalanceVariant(data.creditBalance.percentage),
      progressValue: data.creditBalance.percentage,
      showProgress: true,
      priority: 'essential' as const
    },
    {
      title: 'Success Rate',
      value: `${data.successRate.percentage.toFixed(1)}%`,
      description: data.successRate.percentage > 95 ? 'Excellent performance' :
                   data.successRate.percentage > 90 ? 'Good performance' : 'Needs attention',
      icon: <Target className="h-4 w-4" />,
      trend: data.successRate.trend,
      trendValue: undefined,
      variant: getSuccessRateVariant(data.successRate.percentage),
      progressValue: undefined,
      showProgress: false,
      priority: 'essential' as const
    },
    {
      title: 'This Month',
      value: data.monthlyUsage.jobsCompleted.toLocaleString(),
      description: `${data.monthlyUsage.creditsUsed.toLocaleString()} credits used`,
      icon: <Calendar className="h-4 w-4" />,
      trend: data.monthlyUsage.percentageChange > 0 ? 'up' as const : 
              data.monthlyUsage.percentageChange < 0 ? 'down' as const : 'stable' as const,
      trendValue: data.monthlyUsage.percentageChange,
      variant: 'primary' as const,
      progressValue: undefined,
      showProgress: false,
      priority: 'essential' as const
    }
  ];

  // Additional detailed metrics (collapsible)
  const detailedMetrics = [
    {
      title: 'Total Jobs',
      value: data.totalJobs.count.toLocaleString(),
      description: 'All-time processing jobs',
      icon: <FileText className="h-4 w-4" />,
      trend: data.totalJobs.trend,
      trendValue: data.totalJobs.percentageChange,
      variant: 'neutral' as const,
      progressValue: undefined,
      showProgress: false,
      priority: 'detailed' as const
    },
    {
      title: 'Avg Confidence',
      value: `${data.averageConfidence.score.toFixed(1)}%`,
      description: 'AI matching accuracy',
      icon: <Brain className="h-4 w-4" />,
      trend: data.averageConfidence.trend,
      trendValue: undefined,
      variant: getConfidenceVariant(data.averageConfidence.score),
      progressValue: undefined,
      showProgress: false,
      priority: 'detailed' as const
    }
  ];

  const allMetrics = [...essentialMetrics, ...(showDetailedMetrics ? detailedMetrics : [])];

  return (
    <div className={clsx('space-y-4', className)} role="region" aria-label="Key performance metrics">
      {/* Essential Metrics - Always Visible */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {essentialMetrics.map((metric, index) => (
          <MetricCard
            key={`essential-${index}`}
            title={metric.title}
            value={metric.value}
            description={metric.description}
            icon={metric.icon}
            trend={metric.trend}
            trendValue={metric.trendValue}
            variant={metric.variant}
            progressValue={metric.progressValue}
            showProgress={metric.showProgress}
            priority={metric.priority}
          />
        ))}
      </div>

      {/* Progressive Disclosure Toggle */}
      <div className="flex justify-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowDetailedMetrics(!showDetailedMetrics)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {showDetailedMetrics ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              Show Less Metrics
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              Show All Metrics
            </>
          )}
        </Button>
      </div>

      {/* Detailed Metrics - Collapsible */}
      {showDetailedMetrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          {detailedMetrics.map((metric, index) => (
            <MetricCard
              key={`detailed-${index}`}
              title={metric.title}
              value={metric.value}
              description={metric.description}
              icon={metric.icon}
              trend={metric.trend}
              trendValue={metric.trendValue}
              variant={metric.variant}
              progressValue={metric.progressValue}
              showProgress={metric.showProgress}
              priority={metric.priority}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const MetricsBarSkeleton: React.FC<{ className?: string }> = ({ 
  className = '' 
}) => {
  return (
    <div className={clsx('space-y-4', className)} role="status" aria-label="Loading metrics">
      {/* Essential metrics skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, index) => (
          <Card key={`skeleton-${index}`} className="animate-pulse border">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 bg-gray-300 rounded w-1/2"></div>
              <div className="h-4 w-4 bg-gray-300 rounded"></div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="h-5 bg-gray-300 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-300 rounded w-full mb-2"></div>
              <div className="flex items-center space-x-1">
                <div className="h-3 w-3 bg-gray-300 rounded"></div>
                <div className="h-3 bg-gray-300 rounded w-1/2"></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      {/* Toggle button skeleton */}
      <div className="flex justify-center">
        <div className="h-6 bg-gray-300 rounded w-24 animate-pulse"></div>
      </div>
    </div>
  );
};

export default MetricsBar;