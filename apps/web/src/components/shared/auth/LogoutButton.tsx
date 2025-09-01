/**
 * Reusable logout button component
 */
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/shared/ui/button'
import { LogOut } from 'lucide-react'

interface LogoutButtonProps {
  children?: React.ReactNode
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  className?: string
  redirectTo?: string
  showIcon?: boolean
  onLogoutStart?: () => void
  onLogoutComplete?: () => void
}

export function LogoutButton({
  children,
  variant = 'destructive',
  size = 'default',
  className = '',
  redirectTo = '/',
  showIcon = true,
  onLogoutStart,
  onLogoutComplete,
}: LogoutButtonProps) {
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const router = useRouter()
  const { logout, isLoading } = useAuth()

  const handleLogout = async () => {
    setIsLoggingOut(true)
    onLogoutStart?.()
    
    try {
      await logout()
      onLogoutComplete?.()
      router.push(redirectTo)
    } catch (error) {
      console.error('Logout failed:', error)
      // Even if logout fails, try to redirect
      router.push(redirectTo)
    } finally {
      setIsLoggingOut(false)
    }
  }

  const isDisabled = isLoggingOut || isLoading

  return (
    <Button
      onClick={handleLogout}
      disabled={isDisabled}
      variant={variant}
      size={size}
      className={className}
    >
      {showIcon && (
        <LogOut 
          className={`w-4 h-4 ${children ? 'mr-2' : ''} ${isLoggingOut ? 'animate-spin' : ''}`} 
        />
      )}
      {children || (isLoggingOut ? 'Signing Out...' : 'Sign Out')}
    </Button>
  )
}