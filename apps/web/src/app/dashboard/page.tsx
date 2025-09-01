/**
 * Simplified dashboard page - Clean, focused metrics and job management
 */
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import SimplifiedMetrics, { type SimplifiedMetricsData } from '@/components/dashboard/SimplifiedMetrics'
import AnalyticsCharts from '@/components/dashboard/AnalyticsCharts'
import { EnhancedJobsTable, type JobData } from '@/components/dashboard/EnhancedJobsTable'
import { EmptyDashboard } from '@/components/dashboard/EmptyStates'
import { DashboardSkeleton } from '@/components/dashboard/SkeletonLoaders'
import {
  Upload,
  ChevronUp,
  ChevronDown,
  BarChart3,
} from 'lucide-react'
import Link from 'next/link'
import type { UserStatistics } from '@shared/types'

export default function DashboardPage() {
  const { user, session } = useAuth()
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAnalytics, setShowAnalytics] = useState(false)

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

  // Transform UserStatistics to SimplifiedMetricsData format
  const getSimplifiedMetricsData = (stats: UserStatistics): SimplifiedMetricsData => {
    return {
      credits: {
        value: stats.creditBalance.remaining,
        label: `of ${stats.creditBalance.total.toLocaleString()} total`
      },
      totalJobs: {
        value: stats.totalJobs,
        label: 'All time'
      },
      successRate: {
        value: stats.successRate,
        unit: '%'
      },
      monthlyUsage: {
        jobs: stats.monthlyUsage.jobsCompleted,
        credits: stats.monthlyUsage.creditsUsed,
        label: `${stats.monthlyUsage.month} ${stats.monthlyUsage.year}`
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
    <div className="space-y-6 p-6">
      {/* Simplified Top Metrics Bar */}
      <SimplifiedMetrics 
        data={statistics ? getSimplifiedMetricsData(statistics) : undefined}
        loading={loading}
        className="mb-4"
      />

      {/* Quick Upload Button */}
      <div className="flex justify-center">
        <Button asChild size="lg" className="shadow-md">
          <Link href="/dashboard/upload">
            <Upload className="mr-2 h-5 w-5" />
            Загрузить новый файл
          </Link>
        </Button>
      </div>

      {/* Recent Processing Jobs Table */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Последние задачи обработки</CardTitle>
              <CardDescription>
                Ваши последние операции по обработке файлов
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard/history">Показать все</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-0">
          <EnhancedJobsTable
            jobs={mockJobs}
            loading={loading}
            onJobAction={(action, jobIds) => {
              console.log(`Action: ${action} on jobs:`, jobIds)
              if (action === 'download') {
                jobIds.forEach(jobId => {
                  const job = mockJobs.find(j => j.id === jobId)
                  if (job?.downloadUrl) {
                    window.open(job.downloadUrl, '_blank')
                  }
                })
              }
            }}
            onJobDetails={(jobId) => {
              console.log('View details for job:', jobId)
            }}
            onRefresh={() => {
              console.log('Refresh jobs table')
            }}
          />
        </CardContent>
      </Card>

      {/* Collapsible Analytics & Charts Section */}
      <Card>
        <CardHeader 
          className="cursor-pointer select-none"
          onClick={() => setShowAnalytics(!showAnalytics)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-gray-600" />
              <CardTitle className="text-lg">Аналитика и графики</CardTitle>
            </div>
            <Button variant="ghost" size="sm">
              {showAnalytics ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
          {!showAnalytics && (
            <CardDescription>
              Нажмите для просмотра подробных метрик производительности и трендов
            </CardDescription>
          )}
        </CardHeader>
        {showAnalytics && (
          <CardContent>
            <AnalyticsCharts 
              statistics={statistics || undefined}
              loading={loading}
            />
          </CardContent>
        )}
      </Card>
    </div>
  )
}