import * as React from 'react'
import { cn } from '@/lib/utils'
import { Eye, EyeOff, Lock, CheckCircle2, XCircle } from 'lucide-react'
import { Button } from './button'

export interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  showStrength?: boolean
  showRequirements?: boolean
  onStrengthChange?: (strength: number) => void
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, showStrength = false, showRequirements = false, onStrengthChange, value, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false)
    const [isFocused, setIsFocused] = React.useState(false)
    const password = value as string || ''
    
    // Password strength calculation
    const calculateStrength = (pass: string): number => {
      let strength = 0
      if (pass.length >= 8) strength++
      if (pass.length >= 12) strength++
      if (/[a-z]/.test(pass) && /[A-Z]/.test(pass)) strength++
      if (/\d/.test(pass)) strength++
      if (/[^a-zA-Z0-9]/.test(pass)) strength++
      return Math.min(strength, 5)
    }
    
    const strength = calculateStrength(password)
    
    React.useEffect(() => {
      if (onStrengthChange) {
        onStrengthChange(strength)
      }
    }, [strength, onStrengthChange])
    
    const getStrengthColor = () => {
      if (strength <= 1) return 'bg-red-500'
      if (strength <= 2) return 'bg-orange-500'
      if (strength <= 3) return 'bg-yellow-500'
      if (strength <= 4) return 'bg-lime-500'
      return 'bg-green-500'
    }
    
    const getStrengthText = () => {
      if (strength === 0) return ''
      if (strength <= 1) return 'Weak'
      if (strength <= 2) return 'Fair'
      if (strength <= 3) return 'Good'
      if (strength <= 4) return 'Strong'
      return 'Very Strong'
    }
    
    const requirements = [
      { met: password.length >= 8, text: 'At least 8 characters' },
      { met: /[A-Z]/.test(password), text: 'One uppercase letter' },
      { met: /[a-z]/.test(password), text: 'One lowercase letter' },
      { met: /\d/.test(password), text: 'One number' },
      { met: /[^a-zA-Z0-9]/.test(password), text: 'One special character' },
    ]
    
    return (
      <div className="space-y-2">
        <div className="relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors duration-200">
            <Lock className={cn(
              "h-5 w-5",
              isFocused && "text-blue-500",
              strength > 0 && getStrengthColor().replace('bg-', 'text-')
            )} />
          </div>
          
          <input
            type={showPassword ? "text" : "password"}
            className={cn(
              "flex h-11 w-full rounded-lg border bg-white pl-10 pr-12 py-2 text-sm transition-all duration-200",
              "placeholder:text-gray-400",
              "focus:outline-none focus:ring-2 focus:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-50",
              isFocused ? "border-blue-500 focus:ring-blue-500/20" :
              "border-gray-200 hover:border-gray-300 focus:border-blue-500 focus:ring-blue-500/20",
              className
            )}
            ref={ref}
            value={value}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            {...props}
          />
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 p-0 hover:bg-transparent"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4 text-gray-400 hover:text-gray-600" />
            ) : (
              <Eye className="h-4 w-4 text-gray-400 hover:text-gray-600" />
            )}
          </Button>
        </div>
        
        {showStrength && password.length > 0 && (
          <div className="space-y-1.5 animate-in fade-in-50 slide-in-from-top-1">
            <div className="flex items-center justify-between">
              <div className="flex gap-1 flex-1">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "h-1 flex-1 rounded-full transition-all duration-300",
                      i < strength ? getStrengthColor() : "bg-gray-200"
                    )}
                  />
                ))}
              </div>
              {getStrengthText() && (
                <span className={cn(
                  "text-xs font-medium ml-2",
                  getStrengthColor().replace('bg-', 'text-')
                )}>
                  {getStrengthText()}
                </span>
              )}
            </div>
          </div>
        )}
        
        {showRequirements && isFocused && password.length > 0 && (
          <div className="space-y-1 p-3 bg-gray-50 rounded-lg animate-in fade-in-50 slide-in-from-top-1">
            <p className="text-xs font-medium text-gray-600 mb-2">Password requirements:</p>
            {requirements.map((req, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {req.met ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-gray-300" />
                )}
                <span className={cn(
                  "transition-colors",
                  req.met ? "text-green-700" : "text-gray-500"
                )}>
                  {req.text}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
)

PasswordInput.displayName = "PasswordInput"

export { PasswordInput }