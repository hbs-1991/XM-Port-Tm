import * as React from 'react'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'
import { Button, ButtonProps } from './button'

export interface LoadingButtonProps extends ButtonProps {
  loading?: boolean
  loadingText?: string
  success?: boolean
  successText?: string
}

export const LoadingButton = React.forwardRef<HTMLButtonElement, LoadingButtonProps>(
  ({ 
    className, 
    children, 
    loading, 
    loadingText, 
    success, 
    successText, 
    disabled,
    ...props 
  }, ref) => {
    const [showSuccess, setShowSuccess] = React.useState(false)
    
    React.useEffect(() => {
      if (success) {
        setShowSuccess(true)
        const timer = setTimeout(() => setShowSuccess(false), 3000)
        return () => clearTimeout(timer)
      }
    }, [success])
    
    return (
      <Button
        ref={ref}
        className={cn(
          "relative transition-all duration-300",
          (loading || showSuccess) && "pl-10",
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {/* Loading spinner */}
        {loading && (
          <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin" />
        )}
        
        {/* Success checkmark */}
        {showSuccess && !loading && (
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-in zoom-in-50 fade-in-50"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
        
        {/* Button text */}
        <span className={cn(
          "transition-all duration-300",
          (loading || showSuccess) && "ml-2"
        )}>
          {loading ? (loadingText || children) : 
           showSuccess ? (successText || 'Success!') : 
           children}
        </span>
      </Button>
    )
  }
)

LoadingButton.displayName = 'LoadingButton'