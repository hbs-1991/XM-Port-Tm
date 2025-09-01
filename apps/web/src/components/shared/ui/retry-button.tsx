'use client'

import React, { useState } from 'react'
import { Button } from './button'
import { RefreshCw, Wifi, WifiOff } from 'lucide-react'

interface RetryButtonProps {
  onRetry: () => Promise<void> | void
  loading?: boolean
  disabled?: boolean
  children?: React.ReactNode
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'sm' | 'default' | 'lg'
  showConnectionStatus?: boolean
  maxRetries?: number
}

export const RetryButton: React.FC<RetryButtonProps> = ({
  onRetry,
  loading = false,
  disabled = false,
  children = 'Try Again',
  variant = 'outline',
  size = 'default',
  showConnectionStatus = false,
  maxRetries = 3
}) => {
  const [retrying, setRetrying] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  React.useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const handleRetry = async () => {
    if (retryCount >= maxRetries) {
      return
    }

    setRetrying(true)
    setRetryCount(prev => prev + 1)

    try {
      await onRetry()
      setRetryCount(0) // Reset on success
    } catch (error) {
      console.error('Retry failed:', error)
    } finally {
      setRetrying(false)
    }
  }

  const isDisabled = disabled || loading || retrying || (retryCount >= maxRetries)

  return (
    <div className="flex items-center gap-2">
      <Button
        onClick={handleRetry}
        disabled={isDisabled}
        variant={variant}
        size={size}
        className="min-w-fit"
      >
        <RefreshCw className={`h-4 w-4 mr-2 ${retrying ? 'animate-spin' : ''}`} />
        {retrying ? 'Retrying...' : children}
        {retryCount > 0 && ` (${retryCount}/${maxRetries})`}
      </Button>
      
      {showConnectionStatus && (
        <div className="flex items-center text-sm text-muted-foreground">
          {isOnline ? (
            <>
              <Wifi className="h-4 w-4 mr-1 text-green-500" />
              <span>Online</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 mr-1 text-red-500" />
              <span>Offline</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default RetryButton