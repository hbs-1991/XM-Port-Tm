/**
 * Empty state components for dashboard
 */
'use client'

import Link from 'next/link'
import { Upload, FileText, BarChart3, Clock, Sparkles } from 'lucide-react'
import { Button } from '@/components/shared/ui/button'
import { Card, CardContent } from '@/components/shared/ui/card'

interface EmptyStateProps {
  className?: string
}

export function EmptyDashboard({ className = '' }: EmptyStateProps) {
  return (
    <div className={`text-center py-16 ${className}`}>
      <div className="mx-auto w-24 h-24 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full flex items-center justify-center mb-6">
        <Upload className="h-12 w-12 text-blue-600" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        Welcome to XM-Port!
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        Upload your first customs declaration file to see AI-powered HS code matching, 
        analytics, and processing history come to life.
      </p>
      <div className="space-y-3">
        <Button asChild size="lg" className="bg-blue-600 hover:bg-blue-700">
          <Link href="/dashboard/upload">
            <Upload className="mr-2 h-5 w-5" />
            Upload Your First File
          </Link>
        </Button>
        <div>
          <Button variant="ghost" asChild>
            <Link href="/dashboard/history" className="text-gray-500">
              View Processing History
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}

export function EmptyProcessingHistory({ className = '' }: EmptyStateProps) {
  return (
    <div className={`text-center py-12 ${className}`}>
      <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
        <FileText className="h-8 w-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        No processing jobs yet
      </h3>
      <p className="text-gray-600 mb-4 max-w-sm mx-auto">
        Upload your first file to start processing customs declarations with AI-powered HS code matching.
      </p>
      <Button asChild>
        <Link href="/dashboard/upload">
          <Upload className="mr-2 h-4 w-4" />
          Upload Files
        </Link>
      </Button>
    </div>
  )
}

export function EmptyAnalytics({ className = '' }: EmptyStateProps) {
  return (
    <div className={`text-center py-12 ${className}`}>
      <div className="mx-auto w-16 h-16 bg-gradient-to-br from-purple-100 to-purple-200 rounded-full flex items-center justify-center mb-4">
        <BarChart3 className="h-8 w-8 text-purple-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Analytics Coming Soon
      </h3>
      <p className="text-gray-600 mb-4 max-w-sm mx-auto">
        Process some files to see detailed analytics about your HS code matching performance.
      </p>
      <Button variant="outline" asChild>
        <Link href="/dashboard/upload">
          <Sparkles className="mr-2 h-4 w-4" />
          Get Started
        </Link>
      </Button>
    </div>
  )
}

export function EmptyRecentJobs({ className = '' }: EmptyStateProps) {
  return (
    <Card className={className}>
      <CardContent className="pt-6">
        <div className="text-center py-8">
          <div className="mx-auto w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <Clock className="h-6 w-6 text-gray-400" />
          </div>
          <p className="text-gray-600 text-sm mb-4">No recent processing jobs</p>
          <Button size="sm" asChild>
            <Link href="/dashboard/upload">
              <Upload className="mr-2 h-4 w-4" />
              Upload Files
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}