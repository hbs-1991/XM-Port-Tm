import * as React from 'react'
import { cn } from '@/lib/utils'
import { LucideIcon, AlertCircle, CheckCircle2 } from 'lucide-react'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: LucideIcon
  error?: string
  success?: boolean
  helperText?: string
  showValidation?: boolean
}

const EnhancedInput = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, icon: Icon, error, success, helperText, showValidation = true, ...props }, ref) => {
    const [isFocused, setIsFocused] = React.useState(false)
    
    return (
      <div className="relative">
        <div className="relative">
          {Icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors duration-200">
              <Icon className={cn(
                "h-5 w-5",
                isFocused && "text-blue-500",
                error && "text-red-500",
                success && "text-green-500"
              )} />
            </div>
          )}
          
          <input
            type={type}
            className={cn(
              "flex h-11 w-full rounded-lg border bg-white px-3 py-2 text-sm transition-all duration-200",
              "placeholder:text-gray-400",
              "focus:outline-none focus:ring-2 focus:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-50",
              Icon && "pl-10",
              showValidation && (error || success) && "pr-10",
              // Border colors
              error ? "border-red-300 focus:border-red-500 focus:ring-red-500/20" :
              success ? "border-green-300 focus:border-green-500 focus:ring-green-500/20" :
              isFocused ? "border-blue-500 focus:ring-blue-500/20" :
              "border-gray-200 hover:border-gray-300 focus:border-blue-500 focus:ring-blue-500/20",
              className
            )}
            ref={ref}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? `${props.id || props.name}-error` : undefined}
            {...props}
          />
          
          {showValidation && (error || success) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {error ? (
                <AlertCircle className="h-5 w-5 text-red-500 animate-in fade-in-50 zoom-in-95" />
              ) : success ? (
                <CheckCircle2 className="h-5 w-5 text-green-500 animate-in fade-in-50 zoom-in-95" />
              ) : null}
            </div>
          )}
        </div>
        
        {(error || helperText) && (
          <p 
            id={`${props.id || props.name}-error`}
            className={cn(
              "mt-1.5 text-sm animate-in fade-in-50 slide-in-from-top-1",
              error ? "text-red-600" : "text-gray-500"
            )}
            role={error ? "alert" : undefined}
            aria-live={error ? "polite" : undefined}
          >
            {error || helperText}
          </p>
        )}
      </div>
    )
  }
)

EnhancedInput.displayName = "EnhancedInput"

export { EnhancedInput }