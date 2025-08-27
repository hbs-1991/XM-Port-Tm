import * as React from 'react'
import { cn } from '@/lib/utils'
import { CheckCircle2, XCircle, AlertCircle, Info, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastProps {
  id: string
  type: ToastType
  title: string
  description?: string
  duration?: number
  onClose?: (id: string) => void
}

const toastIcons = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertCircle,
  info: Info,
}

const toastStyles = {
  success: 'bg-green-50 border-green-200 text-green-900',
  error: 'bg-red-50 border-red-200 text-red-900',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-900',
  info: 'bg-blue-50 border-blue-200 text-blue-900',
}

const iconStyles = {
  success: 'text-green-500',
  error: 'text-red-500',
  warning: 'text-yellow-500',
  info: 'text-blue-500',
}

export function Toast({ id, type, title, description, duration = 5000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = React.useState(false)
  const [isLeaving, setIsLeaving] = React.useState(false)
  const Icon = toastIcons[type]
  
  React.useEffect(() => {
    // Trigger enter animation
    const showTimer = setTimeout(() => setIsVisible(true), 10)
    
    // Auto dismiss
    const dismissTimer = setTimeout(() => {
      handleClose()
    }, duration)
    
    return () => {
      clearTimeout(showTimer)
      clearTimeout(dismissTimer)
    }
  }, [duration])
  
  const handleClose = () => {
    setIsLeaving(true)
    setTimeout(() => {
      onClose?.(id)
    }, 300)
  }
  
  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border shadow-lg transition-all duration-300',
        'transform',
        toastStyles[type],
        isVisible && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      )}
      role="alert"
    >
      <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', iconStyles[type])} />
      
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{title}</p>
        {description && (
          <p className="text-sm mt-1 opacity-90">{description}</p>
        )}
      </div>
      
      <button
        onClick={handleClose}
        className={cn(
          'flex-shrink-0 ml-2 p-1 rounded-md transition-colors',
          'hover:bg-white/50 focus:outline-none focus:ring-2 focus:ring-offset-0',
          type === 'success' && 'focus:ring-green-500',
          type === 'error' && 'focus:ring-red-500',
          type === 'warning' && 'focus:ring-yellow-500',
          type === 'info' && 'focus:ring-blue-500'
        )}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// Toast Container Component
export function ToastContainer({ toasts }: { toasts: ToastProps[] }) {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none max-w-md w-full">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast {...toast} />
        </div>
      ))}
    </div>
  )
}

// Toast Hook for easy usage
export function useToast() {
  const [toasts, setToasts] = React.useState<ToastProps[]>([])
  
  const showToast = React.useCallback((toast: Omit<ToastProps, 'id' | 'onClose'>) => {
    const id = Math.random().toString(36).substr(2, 9)
    const newToast: ToastProps = {
      ...toast,
      id,
      onClose: (toastId) => {
        setToasts((prev) => prev.filter((t) => t.id !== toastId))
      },
    }
    
    setToasts((prev) => [...prev, newToast])
    return id
  }, [])
  
  const hideToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])
  
  return {
    toasts,
    showToast,
    hideToast,
    showSuccess: (title: string, description?: string) =>
      showToast({ type: 'success', title, description }),
    showError: (title: string, description?: string) =>
      showToast({ type: 'error', title, description }),
    showWarning: (title: string, description?: string) =>
      showToast({ type: 'warning', title, description }),
    showInfo: (title: string, description?: string) =>
      showToast({ type: 'info', title, description }),
  }
}