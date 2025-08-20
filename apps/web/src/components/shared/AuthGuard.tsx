/**
 * Authentication guard component for protected routes
 */
'use client'

import { useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

interface AuthGuardProps {
  children: ReactNode
  requiredRole?: string
  fallbackUrl?: string
  allowedRoles?: string[]
}

export function AuthGuard({ 
  children, 
  requiredRole,
  allowedRoles,
  fallbackUrl = '/auth/login' 
}: AuthGuardProps) {
  const router = useRouter()
  const { isAuthenticated, isLoading, user, hasRole, hasAnyRole } = useAuth()

  useEffect(() => {
    if (!isLoading) {
      // Not authenticated - redirect to login
      if (!isAuthenticated) {
        router.push(fallbackUrl)
        return
      }

      // Check role requirements
      if (requiredRole && !hasRole(requiredRole)) {
        router.push('/unauthorized')
        return
      }

      if (allowedRoles && !hasAnyRole(allowedRoles)) {
        router.push('/unauthorized')
        return
      }
    }
  }, [isAuthenticated, isLoading, user, requiredRole, allowedRoles, hasRole, hasAnyRole, router, fallbackUrl])

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // Don't render children until authentication is verified
  if (!isAuthenticated) {
    return null
  }

  // Check role requirements before rendering
  if (requiredRole && !hasRole(requiredRole)) {
    return null
  }

  if (allowedRoles && !hasAnyRole(allowedRoles)) {
    return null
  }

  return <>{children}</>
}