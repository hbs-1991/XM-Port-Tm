/**
 * User profile page with security settings
 */
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { LogOut, Shield, AlertTriangle } from 'lucide-react'
import { LogoutButton } from '@/components/shared/auth/LogoutButton'

export default function ProfilePage() {
  const [isLoggingOutAll, setIsLoggingOutAll] = useState(false)
  const { user, logoutAll, isLoading } = useAuth()
  const router = useRouter()

  const handleLogoutAll = async () => {
    setIsLoggingOutAll(true)
    try {
      await logoutAll()
      router.push('/')
    } catch (error) {
      console.error('Logout from all devices failed:', error)
      // Even if it fails, redirect to home
      router.push('/')
    } finally {
      setIsLoggingOutAll(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile Settings</h1>
        <p className="mt-1 text-sm text-gray-500">Manage your account and security settings</p>
      </div>

      {/* User Information Card */}
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your basic account details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {user && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Name</label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.firstName} {user.lastName}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <p className="mt-1 text-sm text-gray-900">{user.email}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Company</label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.companyName || 'Not specified'}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Role</label>
                <p className="mt-1 text-sm text-gray-900">{user.role}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Credits Remaining</label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.creditsRemaining?.toLocaleString() || '0'}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Account Status</label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.isActive ? 'Active' : 'Inactive'}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Security Settings Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Shield className="w-5 h-5 mr-2" />
            Security Settings
          </CardTitle>
          <CardDescription>Manage your account security and sessions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Session Logout */}
          <div className="flex items-start justify-between p-4 border rounded-lg">
            <div>
              <h3 className="text-sm font-medium text-gray-900">Current Session</h3>
              <p className="text-sm text-gray-500 mt-1">
                Sign out of this device only. You'll remain logged in on other devices.
              </p>
            </div>
            <LogoutButton 
              variant="outline" 
              size="sm"
              className="ml-4"
            >
              Sign Out
            </LogoutButton>
          </div>

          {/* All Sessions Logout */}
          <div className="flex items-start justify-between p-4 border border-orange-200 bg-orange-50 rounded-lg">
            <div>
              <h3 className="text-sm font-medium text-gray-900 flex items-center">
                <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
                All Devices
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Sign out from all devices and browsers. You'll need to log in again on all devices.
              </p>
            </div>
            <Button
              onClick={handleLogoutAll}
              disabled={isLoggingOutAll || isLoading}
              variant="destructive"
              size="sm"
              className="ml-4"
            >
              <LogOut 
                className={`w-4 h-4 mr-2 ${isLoggingOutAll ? 'animate-spin' : ''}`} 
              />
              {isLoggingOutAll ? 'Signing Out...' : 'Sign Out All'}
            </Button>
          </div>

          <div className="text-xs text-gray-500 p-4 bg-gray-50 rounded-lg">
            <strong>Security Tip:</strong> Use "Sign Out All" if you suspect unauthorized access 
            to your account or if you've used XM-Port on a shared or public computer.
          </div>
        </CardContent>
      </Card>

      {/* Placeholder for future profile management */}
      <Card className="bg-gray-50">
        <CardHeader>
          <CardTitle className="text-gray-600">Coming Soon</CardTitle>
          <CardDescription>Additional profile management features will be available in future updates</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Change password</li>
            <li>• Update personal information</li>
            <li>• Notification preferences</li>
            <li>• Account deactivation</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}