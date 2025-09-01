/**
 * User profile page with editable profile information and security settings
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Input } from '@/components/shared/ui/input'
import { Label } from '@/components/shared/ui/label'
import { LogOut, Shield, AlertTriangle, Edit2, Save, X, User } from 'lucide-react'
import { LogoutButton } from '@/components/shared/auth/LogoutButton'
import { toast } from '@/components/shared/ui/use-toast'

interface ProfileFormData {
  firstName: string
  lastName: string
  companyName: string
  country: string
}

interface ProfileUpdateRequest {
  firstName?: string
  lastName?: string
  companyName?: string
  country?: string
}

export default function ProfilePage() {
  const [isLoggingOutAll, setIsLoggingOutAll] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [formData, setFormData] = useState<ProfileFormData>({
    firstName: '',
    lastName: '',
    companyName: '',
    country: ''
  })
  const [originalData, setOriginalData] = useState<ProfileFormData>({
    firstName: '',
    lastName: '',
    companyName: '',
    country: ''
  })

  const { user, logoutAll, isLoading, refreshUser } = useAuth()
  const router = useRouter()

  // Initialize form data when user loads
  useEffect(() => {
    if (user) {
      const userData = {
        firstName: user.firstName || '',
        lastName: user.lastName || '',
        companyName: user.companyName || '',
        country: user.country || ''
      }
      setFormData(userData)
      setOriginalData(userData)
    }
  }, [user])

  const handleLogoutAll = async () => {
    setIsLoggingOutAll(true)
    try {
      await logoutAll()
      router.push('/')
    } catch (error) {
      console.error('Logout from all devices failed:', error)
      router.push('/')
    } finally {
      setIsLoggingOutAll(false)
    }
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const handleCancel = () => {
    setFormData(originalData)
    setIsEditing(false)
  }

  const handleInputChange = (field: keyof ProfileFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSave = async () => {
    if (!user) return

    setIsSaving(true)
    try {
      // Prepare update payload with only changed fields
      const updateData: ProfileUpdateRequest = {}
      
      if (formData.firstName !== originalData.firstName) {
        updateData.firstName = formData.firstName
      }
      if (formData.lastName !== originalData.lastName) {
        updateData.lastName = formData.lastName
      }
      if (formData.companyName !== originalData.companyName) {
        updateData.companyName = formData.companyName
      }
      if (formData.country !== originalData.country) {
        updateData.country = formData.country
      }

      // Only make API call if there are changes
      if (Object.keys(updateData).length === 0) {
        toast({
          title: "No Changes",
          description: "No changes were made to your profile."
        })
        setIsEditing(false)
        return
      }

      const response = await fetch('/api/proxy/users/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      })

      if (!response.ok) {
        throw new Error('Failed to update profile')
      }

      await response.json()

      // Update local state and refresh user data
      setOriginalData(formData)
      setIsEditing(false)
      await refreshUser()

      toast({
        title: "Profile Updated",
        description: "Your profile information has been successfully updated."
      })

    } catch (error) {
      console.error('Error updating profile:', error)
      toast({
        title: "Update Failed",
        description: "Failed to update your profile. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsSaving(false)
    }
  }

  const hasChanges = JSON.stringify(formData) !== JSON.stringify(originalData)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile Settings</h1>
        <p className="mt-1 text-sm text-gray-500">Manage your account and security settings</p>
      </div>

      {/* User Information Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center">
                <User className="w-5 h-5 mr-2" />
                Account Information
              </CardTitle>
              <CardDescription>Your basic account details</CardDescription>
            </div>
            {!isEditing ? (
              <Button
                onClick={handleEdit}
                variant="outline"
                size="sm"
                className="flex items-center"
              >
                <Edit2 className="w-4 h-4 mr-2" />
                Edit Profile
              </Button>
            ) : (
              <div className="flex space-x-2">
                <Button
                  onClick={handleCancel}
                  variant="outline"
                  size="sm"
                  disabled={isSaving}
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  size="sm"
                  disabled={isSaving || !hasChanges}
                >
                  <Save className="w-4 h-4 mr-2" />
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {user && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* First Name */}
              <div>
                <Label htmlFor="firstName">First Name</Label>
                {isEditing ? (
                  <Input
                    id="firstName"
                    value={formData.firstName}
                    onChange={(e) => handleInputChange('firstName', e.target.value)}
                    className="mt-1"
                    placeholder="Enter your first name"
                  />
                ) : (
                  <p className="mt-1 text-sm text-gray-900">
                    {user.firstName || 'Not specified'}
                  </p>
                )}
              </div>

              {/* Last Name */}
              <div>
                <Label htmlFor="lastName">Last Name</Label>
                {isEditing ? (
                  <Input
                    id="lastName"
                    value={formData.lastName}
                    onChange={(e) => handleInputChange('lastName', e.target.value)}
                    className="mt-1"
                    placeholder="Enter your last name"
                  />
                ) : (
                  <p className="mt-1 text-sm text-gray-900">
                    {user.lastName || 'Not specified'}
                  </p>
                )}
              </div>

              {/* Email (Read-only) */}
              <div>
                <Label>Email</Label>
                <p className="mt-1 text-sm text-gray-900">{user.email}</p>
                {isEditing && (
                  <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
                )}
              </div>

              {/* Company */}
              <div>
                <Label htmlFor="companyName">Company Name</Label>
                {isEditing ? (
                  <Input
                    id="companyName"
                    value={formData.companyName}
                    onChange={(e) => handleInputChange('companyName', e.target.value)}
                    className="mt-1"
                    placeholder="Enter your company name"
                  />
                ) : (
                  <p className="mt-1 text-sm text-gray-900">
                    {user.companyName || 'Not specified'}
                  </p>
                )}
              </div>

              {/* Country */}
              <div>
                <Label htmlFor="country">Country</Label>
                {isEditing ? (
                  <Input
                    id="country"
                    value={formData.country}
                    onChange={(e) => handleInputChange('country', e.target.value)}
                    className="mt-1"
                    placeholder="Enter your country"
                  />
                ) : (
                  <p className="mt-1 text-sm text-gray-900">
                    {user.country || 'Not specified'}
                  </p>
                )}
              </div>

              {/* Role (Read-only) */}
              <div>
                <Label>Role</Label>
                <p className="mt-1 text-sm text-gray-900">{user.role}</p>
              </div>

              {/* Credits (Read-only) */}
              <div>
                <Label>Credits Remaining</Label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.creditsRemaining?.toLocaleString() || '0'}
                </p>
              </div>

              {/* Account Status (Read-only) */}
              <div>
                <Label>Account Status</Label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.isActive ? 'Active' : 'Inactive'}
                </p>
              </div>
            </div>
          )}

          {isEditing && hasChanges && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-sm text-blue-800">
                You have unsaved changes. Click "Save Changes" to update your profile.
              </p>
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