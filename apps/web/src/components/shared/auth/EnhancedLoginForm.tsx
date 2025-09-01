'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { EnhancedInput } from '@/components/shared/ui/enhanced-input'
import { PasswordInput } from '@/components/shared/ui/password-input'
import { Mail, ArrowRight, Loader2, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface LoginFormData {
  email: string
  password: string
}

interface ValidationErrors {
  email?: string
  password?: string
}

interface EnhancedLoginFormProps {
  onSuccess?: () => void
  redirectTo?: string
}

export function EnhancedLoginForm({ onSuccess, redirectTo = '/dashboard' }: EnhancedLoginFormProps) {
  const router = useRouter()
  const { login, isLoading, error, clearError } = useAuthStore()
  
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: ''
  })
  const [errors, setErrors] = useState<ValidationErrors>({})
  const [touched, setTouched] = useState<{ [key: string]: boolean }>({})
  const [loginSuccess, setLoginSuccess] = useState(false)

  // Real-time validation
  useEffect(() => {
    const newErrors: ValidationErrors = {}
    
    if (touched.email && formData.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(formData.email)) {
        newErrors.email = 'Пожалуйста, введите корректный email адрес'
      }
    }
    
    if (touched.password && formData.password) {
      if (formData.password.length < 6) {
        newErrors.password = 'Пароль должен содержать минимум 6 символов'
      }
    }
    
    setErrors(newErrors)
  }, [formData, touched])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleBlur = (field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }))
  }

  const isFormValid = () => {
    return (
      formData.email &&
      formData.password &&
      Object.keys(errors).length === 0
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    // Handle Escape key to clear focused field
    if (e.key === 'Escape') {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT') {
        target.blur()
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    // Mark all fields as touched
    setTouched({ email: true, password: true })
    
    if (!isFormValid()) {
      // Focus first invalid field for accessibility
      const firstErrorField = document.querySelector('[aria-invalid="true"]') as HTMLInputElement
      if (firstErrorField) {
        firstErrorField.focus()
      }
      return
    }
    
    const success = await login(formData.email, formData.password)
    
    if (success) {
      setLoginSuccess(true)
      onSuccess?.()
      
      // Show success animation before redirect
      setTimeout(() => {
        router.push(redirectTo)
      }, 1000)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-400 rounded-full opacity-10 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-400 rounded-full opacity-10 blur-3xl" />
      </div>

      <Card className={cn(
        "w-full max-w-md relative z-10 border-0 shadow-xl",
        "transition-all duration-500",
        loginSuccess && "scale-95 opacity-90"
      )}>
        <CardHeader className="space-y-1 pb-6">
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center font-bold">
            Добро пожаловать!
          </CardTitle>
          <CardDescription className="text-center">
            Введите ваши данные для входа в аккаунт
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} onKeyDown={handleKeyDown} className="space-y-4" noValidate>
            <EnhancedInput
              icon={Mail}
              type="email"
              name="email"
              placeholder="Введите ваш email"
              value={formData.email}
              onChange={handleChange}
              onBlur={() => handleBlur('email')}
              error={touched.email ? errors.email : undefined}
              success={touched.email && !errors.email && formData.email.length > 0}
              disabled={isLoading}
              required
              autoComplete="email"
              helperText={!touched.email ? "Мы никогда не передадим ваш email третьим лицам" : undefined}
            />

            <PasswordInput
              name="password"
              placeholder="Введите ваш пароль"
              value={formData.password}
              onChange={handleChange}
              onBlur={() => handleBlur('password')}
              disabled={isLoading}
              required
              autoComplete="current-password"
              showStrength={false}
            />

            {(errors.password && touched.password) || error && (
              <p className="text-sm text-red-600 animate-in fade-in-50 slide-in-from-top-1">
                {errors.password || error}
              </p>
            )}

            <div className="flex items-center justify-between pt-2">
              <label 
                className="flex items-center space-x-2 cursor-pointer group relative"
                title="Запомнить меня на 30 дней на этом устройстве"
              >
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 transition-colors"
                />
                <span className="text-sm text-gray-600 group-hover:text-gray-900 transition-colors">
                  Запомнить меня
                </span>
                {/* Tooltip */}
                <div className="absolute bottom-full left-0 mb-2 px-2 py-1 text-xs text-white bg-gray-800 rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 whitespace-nowrap z-10">
                  Оставаться в системе 30 дней
                  <div className="absolute top-full left-3 w-2 h-2 bg-gray-800 transform rotate-45 -mt-1"></div>
                </div>
              </label>
              <Link
                href="/auth/forgot-password"
                className="text-sm text-blue-600 hover:text-blue-700 hover:underline transition-colors"
                aria-label="Сбросить пароль по электронной почте"
              >
                Забыли пароль?
              </Link>
            </div>

            <Button
              type="submit"
              disabled={!isFormValid() || isLoading}
              className={cn(
                "w-full h-11 font-medium transition-all duration-300",
                "bg-gradient-to-r from-blue-600 to-purple-600",
                "hover:from-blue-700 hover:to-purple-700",
                "disabled:from-gray-300 disabled:to-gray-400",
                "shadow-lg hover:shadow-xl hover:-translate-y-0.5",
                loginSuccess && "from-green-500 to-green-600"
              )}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Вход в систему...
                </>
              ) : loginSuccess ? (
                <>
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Успешно!
                </>
              ) : (
                <>
                  Войти
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>

            <div className="relative py-3">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-4 text-gray-500">Или войдите через</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                className="hover:bg-gray-50 transition-colors"
                disabled={isLoading}
              >
                <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Google
              </Button>
              
              <Button
                type="button"
                variant="outline"
                className="hover:bg-gray-50 transition-colors"
                disabled={isLoading}
              >
                <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                GitHub
              </Button>
            </div>
          </form>

          <p className="text-center text-sm text-gray-600 mt-6">
            Нет аккаунта?{' '}
            <Link
              href="/auth/register"
              className="font-medium text-blue-600 hover:text-blue-700 hover:underline transition-colors"
            >
              Зарегистрироваться бесплатно
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}