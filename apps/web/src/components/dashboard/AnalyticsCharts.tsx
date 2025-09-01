/**
 * Analytics Charts component with interactive data visualizations
 */
'use client'

import { useState } from 'react'
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { Badge } from '@/components/shared/ui/badge'
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts'
import { 
  TrendingUp, 
  Calendar, 
  Clock, 
  Target,
  Activity,
  BarChart3
} from 'lucide-react'
import type { UsageAnalytics, UserStatistics } from '@shared/types'

interface AnalyticsChartsProps {
  statistics?: UserStatistics
  analytics?: UsageAnalytics
  loading?: boolean
  className?: string
}

// Sample data for demonstration (would be replaced with real data)
const sampleDailyUsage = [
  { date: '2025-08-20', creditsUsed: 45, jobsCompleted: 3, averageConfidence: 87.5 },
  { date: '2025-08-21', creditsUsed: 62, jobsCompleted: 4, averageConfidence: 91.2 },
  { date: '2025-08-22', creditsUsed: 38, jobsCompleted: 2, averageConfidence: 84.6 },
  { date: '2025-08-23', creditsUsed: 71, jobsCompleted: 5, averageConfidence: 89.8 },
  { date: '2025-08-24', creditsUsed: 29, jobsCompleted: 2, averageConfidence: 88.1 },
  { date: '2025-08-25', creditsUsed: 84, jobsCompleted: 6, averageConfidence: 92.4 },
  { date: '2025-08-26', creditsUsed: 56, jobsCompleted: 4, averageConfidence: 86.7 }
]

const sampleMonthlyTrends = [
  { month: 'Jun', year: 2025, creditsUsed: 1250, jobsCompleted: 85, successRate: 89.4 },
  { month: 'Jul', year: 2025, creditsUsed: 1480, jobsCompleted: 102, successRate: 91.7 },
  { month: 'Aug', year: 2025, creditsUsed: 890, jobsCompleted: 64, successRate: 88.2 }
]

const sampleHourlyUsage = [
  { hour: 9, jobCount: 12, averageProcessingTime: 4500 },
  { hour: 10, jobCount: 18, averageProcessingTime: 3800 },
  { hour: 11, jobCount: 25, averageProcessingTime: 4200 },
  { hour: 12, jobCount: 8, averageProcessingTime: 5100 },
  { hour: 13, jobCount: 15, averageProcessingTime: 3900 },
  { hour: 14, jobCount: 22, averageProcessingTime: 4100 },
  { hour: 15, jobCount: 28, averageProcessingTime: 3600 },
  { hour: 16, jobCount: 20, averageProcessingTime: 4300 }
]

const statusDistribution = [
  { name: 'Completed', value: 85, color: '#10b981' },
  { name: 'Completed with Errors', value: 12, color: '#f59e0b' },
  { name: 'Failed', value: 3, color: '#ef4444' }
]

export function AnalyticsCharts({ 
  statistics, 
  analytics,
  loading = false, 
  className = '' 
}: AnalyticsChartsProps) {
  const [activeTab, setActiveTab] = useState<'daily' | 'monthly' | 'performance'>('daily')

  if (loading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-gray-300 rounded w-1/2"></div>
                <div className="h-3 bg-gray-300 rounded w-3/4"></div>
              </CardHeader>
              <CardContent>
                <div className="h-64 bg-gray-300 rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const formatHour = (hour: number) => {
    return `${hour}:00`
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {`${entry.dataKey}: ${entry.value}`}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Chart Navigation - Responsive */}
      <div className="flex flex-wrap gap-2 sm:space-x-2">
        <Button 
          variant={activeTab === 'daily' ? 'default' : 'outline'}
          onClick={() => setActiveTab('daily')}
          size="sm"
          className="flex-1 sm:flex-none min-w-0"
        >
          <Calendar className="h-4 w-4 mr-1 sm:mr-2" />
          <span className="hidden sm:inline">Daily Usage</span>
          <span className="sm:hidden">Daily</span>
        </Button>
        <Button 
          variant={activeTab === 'monthly' ? 'default' : 'outline'}
          onClick={() => setActiveTab('monthly')}
          size="sm"
          className="flex-1 sm:flex-none min-w-0"
        >
          <TrendingUp className="h-4 w-4 mr-1 sm:mr-2" />
          <span className="hidden sm:inline">Monthly Trends</span>
          <span className="sm:hidden">Monthly</span>
        </Button>
        <Button 
          variant={activeTab === 'performance' ? 'default' : 'outline'}
          onClick={() => setActiveTab('performance')}
          size="sm"
          className="flex-1 sm:flex-none min-w-0"
        >
          <Activity className="h-4 w-4 mr-1 sm:mr-2" />
          <span className="hidden sm:inline">Performance</span>
          <span className="sm:hidden">Perf</span>
        </Button>
      </div>

      {/* Charts Grid - Improved Mobile Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        {/* Primary Chart */}
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {activeTab === 'daily' && 'Daily Usage Trends'}
              {activeTab === 'monthly' && 'Monthly Performance Overview'}
              {activeTab === 'performance' && 'Processing Performance Metrics'}
            </CardTitle>
            <CardDescription>
              {activeTab === 'daily' && 'Daily credit usage and job completion over the past week'}
              {activeTab === 'monthly' && 'Monthly trends in processing volume and success rates'}
              {activeTab === 'performance' && 'Processing performance metrics and timing analysis'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250} className="sm:!h-[300px]">
              {activeTab === 'daily' ? (
                <BarChart data={sampleDailyUsage}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={formatDate}
                    tick={{ fontSize: 10 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="creditsUsed" fill="#3b82f6" name="Credits Used" />
                  <Bar dataKey="jobsCompleted" fill="#10b981" name="Jobs Completed" />
                </BarChart>
              ) : activeTab === 'monthly' ? (
                <LineChart data={sampleMonthlyTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="creditsUsed" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    name="Credits Used"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="jobsCompleted" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    name="Jobs Completed"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="successRate" 
                    stroke="#f59e0b" 
                    strokeWidth={2}
                    name="Success Rate (%)"
                  />
                </LineChart>
              ) : (
                <BarChart data={sampleHourlyUsage}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="hour" 
                    tickFormatter={formatHour}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="jobCount" fill="#8b5cf6" name="Job Count" />
                </BarChart>
              )}
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Processing Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Processing Status
            </CardTitle>
            <CardDescription>
              Distribution of job completion status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200} className="sm:!h-[250px]">
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}%`}
                >
                  {statusDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Confidence Score Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Confidence Trends
            </CardTitle>
            <CardDescription>
              AI matching confidence over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200} className="sm:!h-[250px]">
              <LineChart data={sampleDailyUsage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  tick={{ fontSize: 9 }}
                  angle={-45}
                  textAnchor="end"
                  height={50}
                />
                <YAxis 
                  domain={[80, 95]}
                  tick={{ fontSize: 9 }}
                  width={40}
                />
                <Tooltip 
                  formatter={(value) => [`${value}%`, 'Confidence']}
                  labelFormatter={formatDate}
                />
                <Line 
                  type="monotone" 
                  dataKey="averageConfidence" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                  dot={{ fill: '#ef4444', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Quick Stats Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Performance Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 text-center">
            <div className="p-2 sm:p-0">
              <div className="text-xl sm:text-2xl font-bold text-blue-600">
                {statistics?.processingStats?.totalJobs || 0}
              </div>
              <div className="text-xs sm:text-sm text-gray-600">Total Jobs</div>
            </div>
            <div className="p-2 sm:p-0">
              <div className="text-xl sm:text-2xl font-bold text-green-600">
                {statistics?.processingStats?.successRate?.toFixed(1) || '0'}%
              </div>
              <div className="text-xs sm:text-sm text-gray-600">Success Rate</div>
            </div>
            <div className="p-2 sm:p-0">
              <div className="text-xl sm:text-2xl font-bold text-purple-600">
                {statistics?.averageConfidence?.toFixed(1) || '0'}%
              </div>
              <div className="text-xs sm:text-sm text-gray-600">Avg. Confidence</div>
            </div>
            <div className="p-2 sm:p-0">
              <div className="text-xl sm:text-2xl font-bold text-orange-600">
                {statistics?.monthlyUsage?.creditsUsed || 0}
              </div>
              <div className="text-xs sm:text-sm text-gray-600">Monthly Credits</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default AnalyticsCharts