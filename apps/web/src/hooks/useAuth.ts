/**
 * Custom authentication hook for XM-Port
 */
'use client'

import { useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useAuthStore } from '@/stores/auth'

export function useAuth() {
  const { data: session, status } = useSession()
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    error, 
    setSession,
    login,
    logout,
    register,
    clearError
  } = useAuthStore()

  // Sync NextAuth session with Zustand store
  useEffect(() => {
    setSession(session)
  }, [session, setSession])

  // Helper functions
  const hasRole = (role: string): boolean => {
    return user?.role === role
  }

  const hasAnyRole = (roles: string[]): boolean => {
    return user ? roles.includes(user.role) : false
  }

  const isAdmin = (): boolean => {
    return hasRole('ADMIN')
  }

  const isProjectOwner = (): boolean => {
    return hasRole('PROJECT_OWNER')
  }

  const canAccessAdmin = (): boolean => {
    return hasAnyRole(['ADMIN', 'PROJECT_OWNER'])
  }

  return {
    // State
    user,
    session,
    isAuthenticated,
    isLoading: isLoading || status === 'loading',
    error,
    
    // Actions
    login,
    logout,
    register,
    clearError,
    
    // Role helpers
    hasRole,
    hasAnyRole,
    isAdmin,
    isProjectOwner,
    canAccessAdmin,
  }
}