/**
 * Enhanced Login Page Example
 * This demonstrates how to use the new enhanced components
 */
'use client'

import { EnhancedLoginForm } from '@/components/shared/auth/EnhancedLoginForm'
import { ToastContainer, useToast } from '@/components/shared/ui/enhanced-toast'

export default function EnhancedLoginPage() {
  const { toasts } = useToast()

  return (
    <>
      <EnhancedLoginForm />
      <ToastContainer toasts={toasts} />
    </>
  )
}