/**
 * Login page
 */
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { EnhancedLoginForm } from '@/components/shared/auth/EnhancedLoginForm'

export default function LoginPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, router])

  if (isAuthenticated) {
    return null
  }

  return <EnhancedLoginForm />
}