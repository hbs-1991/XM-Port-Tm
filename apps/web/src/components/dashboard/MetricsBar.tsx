/**
 * MetricsBar component showing key performance indicators in responsive cards
 */
'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Progress } from '@/components/shared/ui/progress'
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  CreditCard, 
  FileText, 
  Target, 
  Brain, 
  Calendar 
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
  colorClass: string;
  progressValue?: number;
  showProgress?: boolean;
}

// Utility functions for determining colors based on thresholds
const getCreditBalanceColor = (percentage: number): string => {
  if (percentage > 70) return 'text-green-600 bg-green-50 border-green-200';
  if (percentage >= 30) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
};

const getSuccessRateColor = (percentage: number): string => {
  if (percentage > 95) return 'text-green-600 bg-green-50 border-green-200';
  if (percentage >= 90) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
};

const getConfidenceColor = (score: number): string => {
  if (score > 90) return 'text-green-600 bg-green-50 border-green-200';
  if (score >= 80) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
};

const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
  switch (trend) {
    case 'up':
      return <TrendingUp className="h-4 w-4 text-green-600" />;
    case 'down':
      return <TrendingDown className="h-4 w-4 text-red-600" />;
    case 'stable':
    default:
      return <Minus className="h-4 w-4 text-gray-600" />;
  }
};

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  description,
  icon,
  trend,
  trendValue,
  colorClass,
  progressValue,
  showProgress = false
}) => {
  return (
    <Card className={clsx('transition-all hover:shadow-md', colorClass)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          {title}
        </CardTitle>
        <div className="h-5 w-5 text-muted-foreground">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold mb-1" aria-label={`${title}: ${value}`}>
          {value}
        </div>
        <CardDescription className="text-xs text-muted-foreground mb-3">
          {description}
        </CardDescription>
        
        {showProgress && progressValue !== undefined && (
          <div className="mb-3">
            <Progress 
              value={progressValue} 
              className="h-2"
              aria-label={`${title} progress: ${progressValue}%`}
            />
          </div>
        )}
        
        {trend && trendValue !== undefined && (
          <div className="flex items-center space-x-1" role="status" aria-live="polite">
            {getTrendIcon(trend)}
            <span className={clsx(
              'text-xs font-medium',
              trend === 'up' ? 'text-green-600' : 
              trend === 'down' ? 'text-red-600' : 
              'text-gray-600'
            )}>
              {trend === 'stable' ? 'No change' : `${Math.abs(trendValue)}%`}
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
  if (loading || !data) {
    return <MetricsBarSkeleton className={className} />;
  }

  const metrics = [
    {
      title: 'Credit Balance',
      value: `${data.creditBalance.remaining.toLocaleString()}`,
      description: `${data.creditBalance.percentage.toFixed(1)}% of total credits`,
      icon: <CreditCard className="h-5 w-5" />,
      trend: data.creditBalance.trend,
      trendValue: undefined, // Credit balance doesn't show percentage change
      colorClass: getCreditBalanceColor(data.creditBalance.percentage),
      progressValue: data.creditBalance.percentage,
      showProgress: true
    },
    {
      title: 'Total Jobs',
      value: data.totalJobs.count.toLocaleString(),
      description: 'Processing jobs completed',
      icon: <FileText className="h-5 w-5" />,
      trend: data.totalJobs.trend,
      trendValue: data.totalJobs.percentageChange,
      colorClass: 'text-blue-600 bg-blue-50 border-blue-200',
      showProgress: false
    },
    {
      title: 'Success Rate',
      value: `${data.successRate.percentage.toFixed(1)}%`,
      description: 'Successfully processed files',
      icon: <Target className="h-5 w-5" />,
      trend: data.successRate.trend,
      trendValue: undefined, // Success rate shows trend without percentage
      colorClass: getSuccessRateColor(data.successRate.percentage),
      showProgress: false
    },
    {
      title: 'Avg Confidence',
      value: `${data.averageConfidence.score.toFixed(1)}%`,
      description: 'ML matching confidence',
      icon: <Brain className="h-5 w-5" />,
      trend: data.averageConfidence.trend,
      trendValue: undefined, // Confidence shows trend without percentage
      colorClass: getConfidenceColor(data.averageConfidence.score),
      showProgress: false
    },
    {
      title: 'This Month',
      value: data.monthlyUsage.jobsCompleted.toLocaleString(),
      description: `${data.monthlyUsage.creditsUsed.toLocaleString()} credits used`,
      icon: <Calendar className="h-5 w-5" />,
      trend: data.monthlyUsage.percentageChange > 0 ? 'up' as const : 
              data.monthlyUsage.percentageChange < 0 ? 'down' as const : 'stable' as const,
      trendValue: data.monthlyUsage.percentageChange,
      colorClass: 'text-purple-600 bg-purple-50 border-purple-200',
      showProgress: false
    }
  ];

  return (
    <div 
      className={clsx(
        'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4',
        className
      )}
      role="region"
      aria-label="Key performance metrics"
    >
      {metrics.map((metric, index) => (
        <MetricCard
          key={index}
          title={metric.title}
          value={metric.value}
          description={metric.description}
          icon={metric.icon}
          trend={metric.trend}
          trendValue={metric.trendValue}
          colorClass={metric.colorClass}
          progressValue={metric.progressValue}
          showProgress={metric.showProgress}
        />
      ))}
    </div>
  );
};

export const MetricsBarSkeleton: React.FC<{ className?: string }> = ({ 
  className = '' 
}) => {
  return (
    <div 
      className={clsx(
        'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4',
        className
      )}
      role="status"
      aria-label="Loading metrics"
    >
      {Array.from({ length: 5 }).map((_, index) => (
        <Card key={index} className="animate-pulse">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="h-4 bg-gray-300 rounded w-1/2"></div>
            <div className="h-5 w-5 bg-gray-300 rounded"></div>
          </CardHeader>
          <CardContent>
            <div className="h-6 bg-gray-300 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-300 rounded w-full mb-3"></div>
            <div className="flex items-center space-x-1">
              <div className="h-4 w-4 bg-gray-300 rounded"></div>
              <div className="h-3 bg-gray-300 rounded w-1/3"></div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default MetricsBar;