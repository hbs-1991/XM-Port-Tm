/**
 * Enhanced empty state components with improved UX and contextual CTAs
 */
'use client'

import Link from 'next/link'
import { Upload, FileText, BarChart3, Clock, Sparkles, Play, CheckCircle, ArrowRight } from 'lucide-react'
import { Button } from '@/components/shared/ui/button'
import { Card, CardContent } from '@/components/shared/ui/card'

interface EmptyStateProps {
  className?: string
}

export function EmptyDashboard({ className = '' }: EmptyStateProps) {
  return (
    <div className={`text-center py-16 px-6 ${className}`}>
      {/* Hero Icon */}
      <div className="mx-auto w-32 h-32 bg-gradient-to-br from-blue-50 to-blue-100 rounded-full flex items-center justify-center mb-8 shadow-lg">
        <Upload className="h-16 w-16 text-blue-600" />
      </div>
      
      {/* Main Content */}
      <div className="max-w-2xl mx-auto mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to XM-Port!
        </h1>
        <p className="text-lg text-gray-600 mb-6 leading-relaxed">
          Transform your customs processing with AI-powered HS code matching. 
          Upload your first file to unlock powerful analytics and streamline your workflow.
        </p>
      </div>

      {/* Quick Start Steps */}
      <div className="max-w-md mx-auto mb-8">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
          Get Started in 3 Steps
        </h3>
        <div className="space-y-3 text-sm text-gray-600">
          <div className="flex items-center justify-center space-x-3">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold text-xs">1</div>
            <span>Upload your Excel/CSV file</span>
          </div>
          <div className="flex items-center justify-center space-x-3">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold text-xs">2</div>
            <span>AI matches HS codes automatically</span>
          </div>
          <div className="flex items-center justify-center space-x-3">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold text-xs">3</div>
            <span>Download processed results</span>
          </div>
        </div>
      </div>

      {/* Primary CTA */}
      <div className="space-y-4">
        <Button asChild size="lg" className="h-14 px-8 text-base font-medium shadow-lg">
          <Link href="/dashboard/upload">
            <Upload className="mr-3 h-5 w-5" />
            Upload Your First File
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        
        {/* Sample Data Option */}
        <p className="text-sm text-gray-500">
          Don't have a file ready?{' '}
          <Button variant="link" className="p-0 h-auto text-sm text-blue-600">
            Try with sample data
          </Button>
        </p>
      </div>
    </div>
  )
}

export function EmptyProcessingHistory({ className = '' }: EmptyStateProps) {
  return (
    <div className={`text-center py-12 px-6 ${className}`}>
      <div className="mx-auto w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mb-6 border-2 border-dashed border-gray-300">
        <FileText className="h-10 w-10 text-gray-400" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-3">
        No processing jobs yet
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto leading-relaxed">
        Your processing history will appear here once you upload and process your first customs declaration file.
      </p>
      
      <div className="space-y-3">
        <Button asChild size="lg" className="h-12 px-6">
          <Link href="/dashboard/upload">
            <Upload className="mr-2 h-4 w-4" />
            Process Your First File
          </Link>
        </Button>
        
        <div className="text-xs text-gray-500">
          Supported formats: Excel (.xlsx), CSV (.csv)
        </div>
      </div>
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
    <Card className={`border-dashed border-2 ${className}`}>
      <CardContent className="pt-6">
        <div className="text-center py-8">
          <div className="mx-auto w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mb-4 border-2 border-blue-200">
            <Clock className="h-8 w-8 text-blue-600" />
          </div>
          <h4 className="font-semibold text-gray-900 mb-2">No recent activity</h4>
          <p className="text-gray-600 text-sm mb-4 max-w-xs mx-auto leading-relaxed">
            Your recent processing jobs will appear here
          </p>
          <Button size="sm" asChild className="h-10">
            <Link href="/dashboard/upload">
              <Upload className="mr-2 h-4 w-4" />
              Start Processing
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}