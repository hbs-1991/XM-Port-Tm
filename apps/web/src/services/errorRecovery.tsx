'use client'

import React from 'react'

interface RetryOptions {
  maxRetries: number
  baseDelay: number
  maxDelay: number
  backoffMultiplier: number
  retryCondition?: (error: any) => boolean
}

interface RetryState {
  attempt: number
  totalAttempts: number
  nextRetryIn: number
  isRetrying: boolean
  error: Error | null
}

export class ErrorRecoveryService {
  private static instance: ErrorRecoveryService
  private retryStates = new Map<string, RetryState>()

  static getInstance(): ErrorRecoveryService {
    if (!ErrorRecoveryService.instance) {
      ErrorRecoveryService.instance = new ErrorRecoveryService()
    }
    return ErrorRecoveryService.instance
  }

  /**
   * Execute a function with exponential backoff retry logic
   */
  async executeWithRetry<T>(
    operationId: string,
    operation: () => Promise<T>,
    options: Partial<RetryOptions> = {}
  ): Promise<T> {
    const opts: RetryOptions = {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 30000,
      backoffMultiplier: 2,
      retryCondition: (error) => this.shouldRetry(error),
      ...options
    }

    let lastError: Error
    
    for (let attempt = 0; attempt <= opts.maxRetries; attempt++) {
      this.updateRetryState(operationId, {
        attempt,
        totalAttempts: opts.maxRetries + 1,
        nextRetryIn: 0,
        isRetrying: attempt > 0,
        error: null
      })

      try {
        const result = await operation()
        this.clearRetryState(operationId)
        return result
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error))
        
        this.updateRetryState(operationId, {
          attempt,
          totalAttempts: opts.maxRetries + 1,
          nextRetryIn: 0,
          isRetrying: false,
          error: lastError
        })

        // Don't retry if this is the last attempt or retry condition fails
        if (attempt === opts.maxRetries || !opts.retryCondition!(lastError)) {
          this.clearRetryState(operationId)
          throw lastError
        }

        // Calculate delay with exponential backoff
        const delay = Math.min(
          opts.baseDelay * Math.pow(opts.backoffMultiplier, attempt),
          opts.maxDelay
        )

        // Update state with countdown
        this.startRetryCountdown(operationId, delay)
        
        console.warn(`Operation ${operationId} failed (attempt ${attempt + 1}/${opts.maxRetries + 1}). Retrying in ${delay}ms...`, lastError)
        
        await this.delay(delay)
      }
    }

    this.clearRetryState(operationId)
    throw lastError!
  }

  /**
   * Check if an error should trigger a retry
   */
  private shouldRetry(error: any): boolean {
    // Network errors
    if (error.name === 'NetworkError' || error.code === 'NETWORK_ERROR') {
      return true
    }

    // Fetch API errors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return true
    }

    // HTTP status codes that should be retried
    if (error.status) {
      const retryableStatuses = [408, 429, 500, 502, 503, 504]
      return retryableStatuses.includes(error.status)
    }

    // Rate limiting
    if (error.message?.toLowerCase().includes('rate limit')) {
      return true
    }

    // Timeout errors
    if (error.message?.toLowerCase().includes('timeout')) {
      return true
    }

    // Connection errors
    if (error.message?.toLowerCase().includes('connection')) {
      return true
    }

    return false
  }

  /**
   * Get current retry state for an operation
   */
  getRetryState(operationId: string): RetryState | null {
    return this.retryStates.get(operationId) || null
  }

  /**
   * Cancel retry for an operation
   */
  cancelRetry(operationId: string): void {
    this.clearRetryState(operationId)
  }

  /**
   * Update retry state
   */
  private updateRetryState(operationId: string, state: RetryState): void {
    this.retryStates.set(operationId, { ...state })
  }

  /**
   * Clear retry state
   */
  private clearRetryState(operationId: string): void {
    this.retryStates.delete(operationId)
  }

  /**
   * Start countdown for next retry
   */
  private startRetryCountdown(operationId: string, delay: number): void {
    const startTime = Date.now()
    
    const updateCountdown = () => {
      const elapsed = Date.now() - startTime
      const remaining = Math.max(0, delay - elapsed)
      
      const currentState = this.retryStates.get(operationId)
      if (currentState) {
        this.updateRetryState(operationId, {
          ...currentState,
          nextRetryIn: Math.ceil(remaining / 1000)
        })
      }

      if (remaining > 0 && this.retryStates.has(operationId)) {
        setTimeout(updateCountdown, 1000)
      }
    }

    updateCountdown()
  }

  /**
   * Utility method for delays
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * Execute with circuit breaker pattern
   */
  async executeWithCircuitBreaker<T>(
    operationId: string,
    operation: () => Promise<T>,
    options: {
      failureThreshold: number
      resetTimeout: number
      monitoringWindow: number
    } = {
      failureThreshold: 5,
      resetTimeout: 60000,
      monitoringWindow: 300000
    }
  ): Promise<T> {
    // This would implement circuit breaker logic
    // For now, fall back to regular retry
    return this.executeWithRetry(operationId, operation)
  }
}

// Export singleton instance
export const errorRecoveryService = ErrorRecoveryService.getInstance()

// React hook for retry states
export function useRetryState(operationId: string) {
  const [state, setState] = React.useState<RetryState | null>(null)
  
  React.useEffect(() => {
    const interval = setInterval(() => {
      const currentState = errorRecoveryService.getRetryState(operationId)
      setState(currentState)
    }, 1000)

    return () => clearInterval(interval)
  }, [operationId])

  const cancelRetry = React.useCallback(() => {
    errorRecoveryService.cancelRetry(operationId)
    setState(null)
  }, [operationId])

  return { state, cancelRetry }
}

// Utility function for API calls with retry
export async function apiCallWithRetry<T>(
  operationId: string,
  apiCall: () => Promise<T>,
  options?: Partial<RetryOptions>
): Promise<T> {
  return errorRecoveryService.executeWithRetry(operationId, apiCall, options)
}

// React component for showing retry status
interface RetryStatusProps {
  operationId: string
  onCancel?: () => void
  className?: string
}

export function RetryStatus({ operationId, onCancel, className = '' }: RetryStatusProps) {
  const { state, cancelRetry } = useRetryState(operationId)

  if (!state || !state.isRetrying) return null

  return (
    <div className={`flex items-center gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg ${className}`}>
      <div className="flex-shrink-0">
        <div className="w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-yellow-800">
          Retrying... (Attempt {state.attempt + 1}/{state.totalAttempts})
        </p>
        {state.nextRetryIn > 0 && (
          <p className="text-xs text-yellow-600">
            Next retry in {state.nextRetryIn}s
          </p>
        )}
      </div>
      <button
        onClick={() => {
          cancelRetry()
          onCancel?.()
        }}
        className="flex-shrink-0 text-yellow-600 hover:text-yellow-800 text-sm font-medium"
      >
        Cancel
      </button>
    </div>
  )
}

export default ErrorRecoveryService