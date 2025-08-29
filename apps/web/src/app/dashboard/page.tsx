/**
 * Main dashboard page showing overview and statistics
 */
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { Badge } from '@/components/shared/ui/badge'
import CreditBalance from '@/components/dashboard/CreditBalance'
import UsageMetrics from '@/components/dashboard/UsageMetrics'
import AnalyticsCharts from '@/components/dashboard/AnalyticsCharts'
import { MetricsBar, type MetricsData } from '@/components/dashboard/MetricsBar'
import { ActionCardsRow, type ActionCardsData } from '@/components/dashboard/ActionCardsRow'
import { EnhancedJobsTable, type JobData } from '@/components/dashboard/EnhancedJobsTable'
import { EmptyDashboard, EmptyRecentJobs } from '@/components/dashboard/EmptyStates'
import { DashboardSkeleton } from '@/components/dashboard/SkeletonLoaders'
import {
  Upload,
  FileText,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowRight,
  BarChart3,
  ChevronUp,
  ChevronDown,
  CreditCard,
  Target,
  Calendar,
} from 'lucide-react'
import Link from 'next/link'
import type { UserStatistics } from '@shared/types'

export default function DashboardPage() {
  const { user, session } = useAuth()
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDetailedAnalytics, setShowDetailedAnalytics] = useState(false)

  const mockJobs: JobData[] = [
    {
      id: '1',
      fileName: 'import_batch_2024_01.xlsx',
      status: 'completed',
      dateCreated: '2024-01-23T14:30:00Z',
      dateCompleted: '2024-01-23T14:45:00Z',
      productsCount: 150,
      confidenceScore: 96.5,
      fileSize: 2048576, // 2MB
      fileType: 'xlsx',
      downloadUrl: '/api/jobs/1/download'
    },
    {
      id: '2',
      fileName: 'export_products_jan.csv',
      status: 'processing',
      dateCreated: '2024-01-23T13:45:00Z',
      productsCount: 87,
      fileSize: 1024000, // 1MB
      fileType: 'csv'
    },
    {
      id: '3',
      fileName: 'customs_declaration.xlsx',
      status: 'completed',
      dateCreated: '2024-01-23T12:20:00Z',
      dateCompleted: '2024-01-23T12:35:00Z',
      productsCount: 234,
      confidenceScore: 93.8,
      fileSize: 3145728, // 3MB
      fileType: 'xlsx',
      downloadUrl: '/api/jobs/3/download'
    },
    {
      id: '4',
      fileName: 'trade_data_february.xlsx',
      status: 'failed',
      dateCreated: '2024-01-23T11:15:00Z',
      productsCount: 0,
      fileSize: 1536000, // 1.5MB
      fileType: 'xlsx',
      errorMessage: 'Invalid file format: Missing required columns'
    },
    {
      id: '5',
      fileName: 'products_list_updated.csv',
      status: 'pending',
      dateCreated: '2024-01-23T10:30:00Z',
      productsCount: 45,
      fileSize: 512000, // 0.5MB
      fileType: 'csv'
    },
    {
      id: '6',
      fileName: 'shipping_manifest_jan.xlsx',
      status: 'completed',
      dateCreated: '2024-01-22T16:45:00Z',
      dateCompleted: '2024-01-22T17:00:00Z',
      productsCount: 78,
      confidenceScore: 89.2,
      fileSize: 1872000, // 1.8MB
      fileType: 'xlsx',
      downloadUrl: '/api/jobs/6/download'
    },
    {
      id: '7',
      fileName: 'customs_form_batch_3.csv',
      status: 'completed',
      dateCreated: '2024-01-22T15:20:00Z',
      dateCompleted: '2024-01-22T15:38:00Z',
      productsCount: 312,
      confidenceScore: 94.7,
      fileSize: 2560000, // 2.5MB
      fileType: 'csv',
      downloadUrl: '/api/jobs/7/download'
    },
    {
      id: '8',
      fileName: 'import_dec_corrected.xlsx',
      status: 'processing',
      dateCreated: '2024-01-22T14:10:00Z',
      productsCount: 156,
      fileSize: 2048000, // 2MB
      fileType: 'xlsx'
    }
  ]

  // Fetch user statistics
  useEffect(() => {
    const fetchStatistics = async () => {
      if (!user) return
      
      try {
        console.log('Fetching statistics for user:', user.email)
        
        const response = await fetch('/api/proxy/api/v1/users/statistics', {
          headers: {
            'Authorization': `Bearer ${session?.accessToken}`,
            'Content-Type': 'application/json',
          },
        })
        
        if (response.ok) {
          const data = await response.json()
          setStatistics(data)
        } else {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`
          try {
            const errorText = await response.text()
            if (errorText) {
              errorMessage += ` - ${errorText}`
            }
            console.error('Statistics API Error:', JSON.stringify({
              status: response.status,
              statusText: response.statusText,
              body: errorText,
              url: response.url
            }, null, 2))
          } catch (parseError) {
            console.error('Failed to parse error response:', parseError)
          }
          throw new Error(`Failed to fetch statistics: ${errorMessage}`)
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load statistics'
        setError(errorMessage)
        console.error('Error fetching statistics:', JSON.stringify({
          error: err instanceof Error ? err.message : String(err),
          message: errorMessage,
          user: user?.email,
          hasToken: !!session?.accessToken
        }, null, 2))
        // Use fallback data for development
        setStatistics({
          totalJobs: 127,
          successRate: 98.5,
          averageConfidence: 94.2,
          monthlyUsage: {
            creditsUsed: 450,
            jobsCompleted: 28,
            filesProcessed: 28,
            averageProcessingTime: 4200,
            month: 'August',
            year: 2025
          },
          creditBalance: {
            remaining: user?.creditsRemaining || 2550,
            total: (user?.creditsRemaining || 2550) + (user?.creditsUsedThisMonth || 450),
            usedThisMonth: user?.creditsUsedThisMonth || 450,
            percentageUsed: user ? (user.creditsUsedThisMonth / (user.creditsRemaining + user.creditsUsedThisMonth)) * 100 : 15,
            subscriptionTier: user?.subscriptionTier || 'BASIC'
          },
          processingStats: {
            totalJobs: 127,
            completedJobs: 124,
            failedJobs: 3,
            successRate: 98.5,
            totalProducts: 3420,
            successfulMatches: 3368,
            averageConfidence: 94.2
          }
        })
      } finally {
        setLoading(false)
      }
    }

    fetchStatistics()
  }, [user])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'processing':
        return <AlertCircle className="h-4 w-4 text-yellow-500 animate-pulse" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      processing: "secondary",
      failed: "destructive",
    }
    return (
      <Badge variant={variants[status] || "outline"}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    )
  }

  // Transform UserStatistics to MetricsData format
  const getMetricsData = (stats: UserStatistics): MetricsData => {
    const creditPercentage = stats.creditBalance.total > 0 
      ? (stats.creditBalance.remaining / stats.creditBalance.total) * 100 
      : 0;

    return {
      creditBalance: {
        remaining: stats.creditBalance.remaining,
        total: stats.creditBalance.total,
        percentage: creditPercentage,
        trend: creditPercentage > 50 ? 'stable' : creditPercentage > 25 ? 'down' : 'down'
      },
      totalJobs: {
        count: stats.totalJobs,
        trend: stats.totalJobs > 100 ? 'up' : stats.totalJobs > 50 ? 'stable' : 'down',
        percentageChange: 12.5 // This would come from API comparing to previous period
      },
      successRate: {
        percentage: stats.successRate,
        trend: stats.successRate > 95 ? 'up' : stats.successRate > 90 ? 'stable' : 'down'
      },
      averageConfidence: {
        score: stats.averageConfidence,
        trend: stats.averageConfidence > 90 ? 'up' : stats.averageConfidence > 85 ? 'stable' : 'down'
      },
      monthlyUsage: {
        creditsUsed: stats.monthlyUsage.creditsUsed,
        jobsCompleted: stats.monthlyUsage.jobsCompleted,
        month: `${stats.monthlyUsage.month} ${stats.monthlyUsage.year}`,
        percentageChange: 8.2 // This would come from API comparing to previous month
      }
    };
  };

  // Transform UserStatistics to ActionCardsData format
  const getActionCardsData = (stats: UserStatistics): ActionCardsData => {
    return {
      upload: {
        allowedTypes: ['.xlsx', '.xls', '.csv'],
        maxSize: 25 * 1024 * 1024, // 25MB
        isUploading: false
      },
      monthlyOverview: {
        currentMonth: {
          creditsUsed: stats.monthlyUsage.creditsUsed,
          jobsCompleted: stats.monthlyUsage.jobsCompleted,
          avgProcessingTime: stats.monthlyUsage.averageProcessingTime
        },
        previousMonth: {
          creditsUsed: Math.round(stats.monthlyUsage.creditsUsed * 0.85), // Mock previous month data
          jobsCompleted: Math.round(stats.monthlyUsage.jobsCompleted * 0.92),
          avgProcessingTime: stats.monthlyUsage.averageProcessingTime + 300
        },
        chartData: [
          { month: 'Jun', jobs: 18, credits: 380 },
          { month: 'Jul', jobs: 24, credits: 420 },
          { month: 'Aug', jobs: stats.monthlyUsage.jobsCompleted, credits: stats.monthlyUsage.creditsUsed }
        ]
      },
      performance: {
        successRate: stats.successRate,
        totalJobs: stats.processingStats.totalJobs,
        successfulJobs: stats.processingStats.completedJobs,
        failedJobs: stats.processingStats.failedJobs,
        pendingJobs: stats.processingStats.totalJobs - stats.processingStats.completedJobs - stats.processingStats.failedJobs
      }
    };
  };

  // Show loading skeleton while fetching data
  if (loading) {
    return <DashboardSkeleton />
  }

  // Show empty dashboard only for truly new users with no data (no statistics at all)
  // If there's an error but we have fallback data, show the dashboard with fallback data
  const shouldShowEmpty = !statistics || (
    statistics.totalJobs === 0 && 
    statistics.processingStats?.totalJobs === 0 &&
    !error // Don't show empty if there's an error with fallback data
  )
  
  if (shouldShowEmpty) {
    return <EmptyDashboard />
  }

  return (
    <div className="space-y-8">
      {/* Hero Section with Upload CTA */}
      <div className="relative">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg -z-10"></div>
        
        <div className="px-6 py-8 sm:px-8 sm:py-12">
          <div className="max-w-4xl mx-auto">
            {/* Welcome Header */}
            <div className="text-center mb-8">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-3">
                Welcome back{user?.firstName ? `, ${user.firstName}` : ''}!
              </h1>
              <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
                Streamline your customs processing with AI-powered HS code matching
              </p>
            </div>

            {/* Primary Action */}
            <div className="flex flex-col sm:flex-row justify-center items-center gap-4 mb-6">
              <Button asChild size="lg" className="w-full sm:w-auto h-14 px-8 text-base font-medium shadow-lg">
                <Link href="/dashboard/upload">
                  <Upload className="mr-3 h-5 w-5" />
                  Upload & Process Files
                </Link>
              </Button>
              <Button variant="outline" asChild size="lg" className="w-full sm:w-auto h-14 px-6 text-base">
                <Link href="/dashboard/history">
                  <FileText className="mr-2 h-4 w-4" />
                  View History
                </Link>
              </Button>
            </div>

            {/* Quick Stats Preview */}
            {statistics && (
              <div className="flex justify-center">
                <div className="inline-flex items-center space-x-6 text-sm text-gray-600 bg-white/70 px-6 py-3 rounded-full backdrop-blur-sm">
                  <div className="flex items-center space-x-2">
                    <CreditCard className="h-4 w-4 text-blue-600" />
                    <span>{statistics.creditBalance.remaining.toLocaleString()} credits</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Target className="h-4 w-4 text-green-600" />
                    <span>{statistics.successRate.toFixed(1)}% success rate</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4 text-purple-600" />
                    <span>{statistics.monthlyUsage.jobsCompleted} jobs this month</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Key Metrics Bar with Progressive Disclosure */}
      <MetricsBar 
        data={statistics ? getMetricsData(statistics) : undefined}
        loading={loading}
      />

      {/* Secondary Action Cards - Reduced Prominence */}
      <ActionCardsRow
        data={statistics ? getActionCardsData(statistics) : undefined}
        loading={loading}
        onFileUpload={(files) => {
          console.log('Files uploaded:', files);
          // TODO: Integrate with actual upload logic
        }}
      />

      {/* Collapsible Analytics Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Detailed Analytics</h2>
            <p className="text-sm text-gray-600">In-depth performance metrics and trends</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDetailedAnalytics(!showDetailedAnalytics)}
            className="flex items-center gap-2"
          >
            {showDetailedAnalytics ? (
              <>
                <ChevronUp className="h-4 w-4" />
                Hide Analytics
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" />
                View Analytics
              </>
            )}
          </Button>
        </div>

        {showDetailedAnalytics && (
          <div className="space-y-6">
            {/* Usage Metrics */}
            <UsageMetrics 
              statistics={statistics || undefined} 
              loading={loading}
            />

            {/* Analytics Charts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Performance Charts
                </CardTitle>
                <CardDescription>
                  Interactive data visualization of your processing performance and trends
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AnalyticsCharts 
                  statistics={statistics || undefined}
                  loading={loading}
                />
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Enhanced Jobs Table */}
      <EnhancedJobsTable
        jobs={mockJobs}
        loading={loading}
        onJobAction={(action, jobIds) => {
          console.log(`Action: ${action} on jobs:`, jobIds);
          // TODO: Integrate with actual job action handlers
          if (action === 'download') {
            // Handle download
            jobIds.forEach(jobId => {
              const job = mockJobs.find(j => j.id === jobId);
              if (job?.downloadUrl) {
                window.open(job.downloadUrl, '_blank');
              }
            });
          } else if (action === 'delete') {
            // Handle delete
            console.log('Delete jobs:', jobIds);
          }
        }}
        onJobDetails={(jobId) => {
          console.log('View details for job:', jobId);
          // TODO: Open job details modal or navigate to details page
        }}
        onRefresh={() => {
          console.log('Refresh jobs table');
          // TODO: Refetch jobs data
        }}
      />

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-600">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm">
                {error} - Using demo data for display
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}