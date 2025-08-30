/**
 * Simplified metrics display component - Clean, focused key metrics only
 */
import React from 'react'
import { CreditCard, Briefcase, TrendingUp, Calendar } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SimplifiedMetricsData {
  credits: {
    value: number
    label?: string
  }
  totalJobs: {
    value: number
    label?: string
  }
  successRate: {
    value: number
    unit?: string
  }
  monthlyUsage: {
    jobs: number
    credits: number
    label?: string
  }
}

interface SimplifiedMetricsProps {
  data?: SimplifiedMetricsData
  loading?: boolean
  className?: string
}

export function SimplifiedMetrics({ 
  data, 
  loading = false,
  className 
}: SimplifiedMetricsProps) {
  
  if (loading) {
    return (
      <div className={cn("bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6", className)}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4 animate-pulse">
              <div className="p-3 bg-gray-200 rounded-lg w-12 h-12" />
              <div className="space-y-2 flex-1">
                <div className="h-4 bg-gray-200 rounded w-20" />
                <div className="h-7 bg-gray-200 rounded w-24" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className={cn(
      "bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 shadow-sm",
      className
    )}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Credits */}
        <div className="flex items-center space-x-4 group">
          <div className="p-3 bg-white rounded-lg shadow-sm group-hover:shadow-md transition-shadow">
            <CreditCard className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <p className="text-sm text-gray-600 font-medium">Credits</p>
            <p className="text-2xl font-bold text-gray-900">
              {data.credits.value.toLocaleString()}
            </p>
            {data.credits.label && (
              <p className="text-xs text-gray-500">{data.credits.label}</p>
            )}
          </div>
        </div>

        {/* Total Jobs */}
        <div className="flex items-center space-x-4 group">
          <div className="p-3 bg-white rounded-lg shadow-sm group-hover:shadow-md transition-shadow">
            <Briefcase className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <p className="text-sm text-gray-600 font-medium">Total Jobs</p>
            <p className="text-2xl font-bold text-gray-900">
              {data.totalJobs.value.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">
              {data.totalJobs.label || 'All time'}
            </p>
          </div>
        </div>

        {/* Success Rate */}
        <div className="flex items-center space-x-4 group">
          <div className="p-3 bg-white rounded-lg shadow-sm group-hover:shadow-md transition-shadow">
            <TrendingUp className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <p className="text-sm text-gray-600 font-medium">Success Rate</p>
            <p className="text-2xl font-bold text-gray-900">
              {data.successRate.value.toFixed(1)}{data.successRate.unit || '%'}
            </p>
          </div>
        </div>

        {/* This Month Usage */}
        <div className="flex items-center space-x-4 group">
          <div className="p-3 bg-white rounded-lg shadow-sm group-hover:shadow-md transition-shadow">
            <Calendar className="h-6 w-6 text-orange-600" />
          </div>
          <div>
            <p className="text-sm text-gray-600 font-medium">This Month</p>
            <p className="text-2xl font-bold text-gray-900">
              {data.monthlyUsage.jobs} jobs
            </p>
            <p className="text-xs text-gray-500">
              {data.monthlyUsage.credits.toLocaleString()} credits used
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SimplifiedMetrics