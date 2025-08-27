/**
 * Usage Metrics component showing processing statistics and analytics
 */
'use client'

import { useState, useEffect } from 'react'
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/shared/ui/card'
import { Badge } from '@/components/shared/ui/badge'
import { Progress } from '@/components/shared/ui/progress'
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Clock, 
  CheckCircle,
  XCircle,
  Target,
  Calendar,
  Activity,
  Minus
} from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/shared/ui/ui/tooltip'
import type { 
  UserStatistics, 
  ProcessingStats, 
  MonthlyUsage 
} from '@shared/types'

interface UsageMetricsProps {
  statistics?: UserStatistics
  loading?: boolean
  className?: string
}

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  trend?: 'up' | 'down' | 'stable'
  trendValue?: number
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'gray'
}

function MetricCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend, 
  trendValue,
  color = 'gray' 
}: MetricCardProps) {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50 border-blue-200',
    green: 'text-green-600 bg-green-50 border-green-200',
    red: 'text-red-600 bg-red-50 border-red-200',
    yellow: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    purple: 'text-purple-600 bg-purple-50 border-purple-200',
    gray: 'text-gray-600 bg-gray-50 border-gray-200'
  }

  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="h-3 w-3 text-green-500" />
    if (trend === 'down') return <TrendingDown className="h-3 w-3 text-red-500" />
    return <Minus className="h-3 w-3 text-gray-400" />
  }

  return (
    <Card className="border border-gray-200">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">{title}</p>
              <div className="flex items-center space-x-2">
                <span className="text-2xl font-bold text-gray-900">
                  {typeof value === 'number' ? value.toLocaleString() : value}
                </span>
                {trend && trendValue && (
                  <div className="flex items-center space-x-1">
                    {getTrendIcon()}
                    <span className={`text-xs font-medium ${
                      trend === 'up' ? 'text-green-600' : 
                      trend === 'down' ? 'text-red-600' : 
                      'text-gray-500'
                    }`}>
                      {trendValue}%
                    </span>
                  </div>
                )}
              </div>
              {subtitle && (
                <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function UsageMetrics({ 
  statistics, 
  loading = false, 
  className = '' 
}: UsageMetricsProps) {
  const [displayStats, setDisplayStats] = useState<UserStatistics | null>(null)

  useEffect(() => {
    if (statistics) {
      setDisplayStats(statistics)
    }
  }, [statistics])

  if (loading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} className="animate-pulse">
              <CardContent className="p-6">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gray-300 rounded-lg"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
                    <div className="h-6 bg-gray-300 rounded w-1/2"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!displayStats) {
    return (
      <div className={className}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Usage Metrics
            </CardTitle>
            <CardDescription>Unable to load usage statistics</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const { processingStats, monthlyUsage } = displayStats

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Jobs"
          value={processingStats?.totalJobs || 0}
          subtitle="All time"
          icon={BarChart3}
          color="blue"
        />
        
        <MetricCard
          title="Success Rate"
          value={`${processingStats?.successRate?.toFixed(1) || '0'}%`}
          subtitle="Processing success"
          icon={CheckCircle}
          color={(processingStats?.successRate || 0) > 90 ? 'green' : (processingStats?.successRate || 0) > 75 ? 'yellow' : 'red'}
        />
        
        <MetricCard
          title="Avg. Confidence"
          value={`${displayStats?.averageConfidence?.toFixed(1) || '0'}%`}
          subtitle="AI matching confidence"
          icon={Target}
          color={(displayStats?.averageConfidence || 0) > 85 ? 'green' : (displayStats?.averageConfidence || 0) > 70 ? 'yellow' : 'red'}
        />
        
        <MetricCard
          title="This Month"
          value={monthlyUsage?.jobsCompleted || 0}
          subtitle={`${monthlyUsage?.month || ''} ${monthlyUsage?.year || ''}`}
          icon={Calendar}
          color="purple"
        />
      </div>

      {/* Detailed Statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Processing Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Processing Performance
            </CardTitle>
            <CardDescription>
              Overview of your file processing statistics
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm text-gray-600">Completed Jobs</span>
                </div>
                <span className="font-semibold text-green-600">
                  {(processingStats?.completedJobs || 0).toLocaleString()}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <XCircle className="h-4 w-4 text-red-500" />
                  <span className="text-sm text-gray-600">Failed Jobs</span>
                </div>
                <span className="font-semibold text-red-600">
                  {(processingStats?.failedJobs || 0).toLocaleString()}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Target className="h-4 w-4 text-blue-500" />
                  <span className="text-sm text-gray-600">Total Products</span>
                </div>
                <span className="font-semibold">
                  {(processingStats?.totalProducts || 0).toLocaleString()}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm text-gray-600">Successful Matches</span>
                </div>
                <span className="font-semibold text-green-600">
                  {(processingStats?.successfulMatches || 0).toLocaleString()}
                </span>
              </div>
            </div>
            
            {/* Success Rate Progress */}
            <div className="pt-4 border-t">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">Match Success Rate</span>
                <span className="font-medium">
                  {(processingStats?.totalProducts || 0) > 0 
                    ? (((processingStats?.successfulMatches || 0) / (processingStats?.totalProducts || 1)) * 100).toFixed(1)
                    : 0
                  }%
                </span>
              </div>
              <Progress 
                value={(processingStats?.totalProducts || 0) > 0 
                  ? ((processingStats?.successfulMatches || 0) / (processingStats?.totalProducts || 1)) * 100
                  : 0
                } 
                className="h-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* Monthly Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Monthly Overview
            </CardTitle>
            <CardDescription>
              {monthlyUsage?.month || ''} {monthlyUsage?.year || ''} performance summary
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {monthlyUsage?.creditsUsed?.toLocaleString() || '0'}
                </div>
                <div className="text-sm text-gray-600">Credits Used</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {monthlyUsage?.filesProcessed?.toLocaleString() || '0'}
                </div>
                <div className="text-sm text-gray-600">Files Processed</div>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-600">Avg. Processing Time</span>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <span className="text-gray-400 cursor-help">ⓘ</span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Average time to process each file</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <span className="font-semibold">
                  {(monthlyUsage?.averageProcessingTime || 0) > 60000 
                    ? `${((monthlyUsage?.averageProcessingTime || 0) / 60000).toFixed(1)}m`
                    : `${((monthlyUsage?.averageProcessingTime || 0) / 1000).toFixed(1)}s`
                  }
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Jobs This Month</span>
                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                  {monthlyUsage?.jobsCompleted || 0}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default UsageMetrics