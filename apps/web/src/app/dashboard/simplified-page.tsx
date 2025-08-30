/**
 * Simplified dashboard page - Clean, focused metrics and job management
 */
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { Badge } from '@/components/shared/ui/badge'
import AnalyticsCharts from '@/components/dashboard/AnalyticsCharts'
import { EnhancedJobsTable, type JobData } from '@/components/dashboard/EnhancedJobsTable'
import {
  CreditCard,
  Briefcase,
  TrendingUp,
  Calendar,
  ChevronDown,
  ChevronUp,
  Upload,
  BarChart3,
} from 'lucide-react'
import Link from 'next/link'
import type { UserStatistics } from '@shared/types'

export default function SimplifiedDashboardPage() {
  const { user, session } = useAuth()
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loading, setLoading] = useState(true)
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
      fileSize: 2048576,
      fileType: 'xlsx',
      downloadUrl: '/api/jobs/1/download'
    },
    {
      id: '2',
      fileName: 'export_products_jan.csv',
      status: 'processing',
      dateCreated: '2024-01-23T13:45:00Z',
      productsCount: 87,
      fileSize: 1024000,
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
      fileSize: 3145728,
      fileType: 'xlsx',
      downloadUrl: '/api/jobs/3/download'
    },
    {
      id: '4',
      fileName: 'trade_data_february.xlsx',
      status: 'failed',
      dateCreated: '2024-01-23T11:15:00Z',
      productsCount: 0,
      fileSize: 1536000,
      fileType: 'xlsx',
      errorMessage: 'Invalid file format: Missing required columns'
    },
    {
      id: '5',
      fileName: 'products_list_updated.csv',
      status: 'pending',
      dateCreated: '2024-01-23T10:30:00Z',
      productsCount: 45,
      fileSize: 512000,
      fileType: 'csv'
    }
  ]

  // Fetch user statistics
  useEffect(() => {
    const fetchStatistics = async () => {
      if (!user) return
      
      try {
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
          // Use fallback data
          setStatistics({
            totalJobs: 127,
            successRate: 98.5,
            averageConfidence: 94.2,
            monthlyUsage: {
              creditsUsed: 450,
              jobsCompleted: 28,
              filesProcessed: 28,
              averageProcessingTime: 4200,
              month: 'January',
              year: 2024
            },
            creditBalance: {
              remaining: user?.creditsRemaining || 2550,
              total: 3000,
              usedThisMonth: 450,
              percentageUsed: 15,
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
        }
      } catch (err) {
        console.error('Error fetching statistics:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchStatistics()
  }, [user, session])

  return (
    <div className="space-y-6 p-6">
      {/* Simplified Top Metrics Bar */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-0 shadow-sm">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Credits */}
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <CreditCard className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">Credits</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statistics?.creditBalance.remaining.toLocaleString() || '0'}
                </p>
              </div>
            </div>

            {/* Total Jobs */}
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <Briefcase className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">Total Jobs</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statistics?.totalJobs || 0}
                </p>
                <p className="text-xs text-gray-500">All time</p>
              </div>
            </div>

            {/* Success Rate */}
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statistics?.successRate.toFixed(1) || '0'}%
                </p>
              </div>
            </div>

            {/* This Month Usage */}
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <Calendar className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">This Month</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statistics?.monthlyUsage.jobsCompleted || 0} jobs
                </p>
                <p className="text-xs text-gray-500">
                  {statistics?.monthlyUsage.creditsUsed || 0} credits used
                </p>
              </div>
            </div>
          </div>

          {/* Quick Action Button */}
          <div className="mt-6 flex justify-center">
            <Button asChild size="lg" className="shadow-md">
              <Link href="/dashboard/upload">
                <Upload className="mr-2 h-5 w-5" />
                Upload New File
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Processing Jobs Table */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Recent Processing Jobs</CardTitle>
              <CardDescription>
                Your latest file processing activities
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard/history">View All</Link>
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

      {/* Collapsible Analytics Section */}
      <Card>
        <CardHeader 
          className="cursor-pointer select-none"
          onClick={() => setShowAnalytics(!showAnalytics)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-gray-600" />
              <CardTitle className="text-lg">Analytics & Charts</CardTitle>
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
              Click to view detailed performance metrics and trends
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