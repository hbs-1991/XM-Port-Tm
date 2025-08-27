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
} from 'lucide-react'
import Link from 'next/link'
import type { UserStatistics } from '@shared/types'

export default function DashboardPage() {
  const { user, session } = useAuth()
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const recentJobs = [
    {
      id: '1',
      fileName: 'import_batch_2024_01.xlsx',
      status: 'completed',
      date: '2024-01-23 14:30',
      products: 150,
      confidence: 96.5,
    },
    {
      id: '2',
      fileName: 'export_products_jan.csv',
      status: 'processing',
      date: '2024-01-23 13:45',
      products: 87,
      confidence: 0,
    },
    {
      id: '3',
      fileName: 'customs_declaration.xlsx',
      status: 'completed',
      date: '2024-01-23 12:20',
      products: 234,
      confidence: 93.8,
    },
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

  // Show loading skeleton while fetching data
  if (loading) {
    return <DashboardSkeleton />
  }

  // Show empty dashboard for new users with no data
  const hasData = statistics && (
    statistics.totalJobs > 0 || 
    statistics.processingStats?.totalJobs > 0
  )
  
  if (!hasData && !error) {
    return <EmptyDashboard />
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.firstName}!
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Here's an overview of your processing activity and account statistics
        </p>
      </div>

      {/* Credit Balance and Upload Section */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <CreditBalance 
            creditBalance={statistics?.creditBalance}
            loading={loading}
          />
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Quick Upload
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Start processing your customs declaration files with AI-powered HS code matching
              </p>
              <Button asChild className="w-full">
                <Link href="/dashboard/upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Files
                </Link>
              </Button>
              <Button variant="outline" asChild className="w-full">
                <Link href="/dashboard/history">
                  <FileText className="mr-2 h-4 w-4" />
                  View History
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

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
            Analytics Dashboard
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

      {/* Recent Jobs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Processing Jobs</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/dashboard/history">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {recentJobs.length > 0 ? (
            <div className="space-y-4">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between rounded-lg border p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center space-x-4">
                    {getStatusIcon(job.status)}
                    <div>
                      <p className="text-sm font-medium">{job.fileName}</p>
                      <p className="text-xs text-gray-500">{job.date}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="text-sm font-medium">{job.products} products</p>
                      {job.confidence > 0 && (
                        <p className="text-xs text-gray-500">
                          {job.confidence}% confidence
                        </p>
                      )}
                    </div>
                    {getStatusBadge(job.status)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No processing jobs yet</p>
              <p className="text-sm text-gray-400 mb-4">
                Upload your first file to get started
              </p>
              <Button asChild>
                <Link href="/dashboard/upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Files
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

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