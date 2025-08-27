/**
 * Test page to verify responsive improvements
 * This is a temporary file for testing - can be removed after verification
 */
'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import MobileNavigation from './MobileNavigation'
import BreadcrumbNavigation from './BreadcrumbNavigation'
import FloatingActionButton from './FloatingActionButton'
import { EmptyDashboard } from './EmptyStates'
import { DashboardSkeleton } from './SkeletonLoaders'
import { Upload, FileText, BarChart3 } from 'lucide-react'

export default function ResponsiveTestPage() {
  const [showSkeleton, setShowSkeleton] = useState(false)
  const [showEmpty, setShowEmpty] = useState(false)

  const mockUser = {
    firstName: 'John',
    lastName: 'Doe',
    email: 'john.doe@example.com',
    creditsRemaining: 2550
  }

  const handleSignOut = () => {
    console.log('Sign out clicked')
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Dashboard UI Test</h1>
          <MobileNavigation 
            user={mockUser}
            onSignOut={handleSignOut}
            isLoggingOut={false}
          />
        </div>

        <BreadcrumbNavigation />

        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Component Tests</CardTitle>
              <CardDescription>Test different UI states</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={() => {
                  setShowSkeleton(!showSkeleton)
                  setShowEmpty(false)
                }}
                variant="outline"
                className="w-full"
              >
                {showSkeleton ? 'Hide' : 'Show'} Loading State
              </Button>
              
              <Button 
                onClick={() => {
                  setShowEmpty(!showEmpty)
                  setShowSkeleton(false)
                }}
                variant="outline"
                className="w-full"
              >
                {showEmpty ? 'Hide' : 'Show'} Empty State
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Sample Content
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                This content shows how cards appear on different screen sizes.
              </p>
              <Button size="sm" className="w-full">
                <Upload className="mr-2 h-4 w-4" />
                Action Button
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Analytics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Total Jobs</span>
                  <span className="font-medium">127</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Success Rate</span>
                  <span className="font-medium">98.5%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Avg Confidence</span>
                  <span className="font-medium">94.2%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {showSkeleton && <DashboardSkeleton />}
        {showEmpty && <EmptyDashboard />}

        {!showSkeleton && !showEmpty && (
          <Card>
            <CardHeader>
              <CardTitle>Responsive Features Implemented</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h4 className="font-semibold mb-2">Mobile Navigation</h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>✅ Sheet-based mobile menu (try the hamburger icon)</li>
                    <li>✅ User profile section in mobile nav</li>
                    <li>✅ Credit balance display</li>
                    <li>✅ Clean logout action</li>
                  </ul>
                </div>
                
                <div>
                  <h4 className="font-semibold mb-2">Enhanced Features</h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>✅ Floating action button (mobile only)</li>
                    <li>✅ Breadcrumb navigation</li>
                    <li>✅ Empty states for new users</li>
                    <li>✅ Skeleton loading states</li>
                    <li>✅ Responsive chart improvements</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <FloatingActionButton />
      </div>
    </div>
  )
}