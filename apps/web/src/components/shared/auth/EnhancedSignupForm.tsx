'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/shared/ui/card'
import { Button } from '@/components/shared/ui/button'
import { EnhancedInput } from '@/components/shared/ui/enhanced-input'
import { PasswordInput } from '@/components/shared/ui/password-input'
import { Mail, User, Building, ArrowRight, Loader2, Sparkles, CheckCircle2 } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface SignupFormData {
  firstName: string
  lastName: string
  email: string
  companyName: string
  password: string
  confirmPassword: string
}

interface ValidationErrors {
  firstName?: string
  lastName?: string
  email?: string
  companyName?: string
  password?: string
  confirmPassword?: string
}

interface EnhancedSignupFormProps {
  onSuccess?: () => void
  redirectTo?: string
}

export function EnhancedSignupForm({ onSuccess, redirectTo = '/dashboard' }: EnhancedSignupFormProps) {
  const router = useRouter()
  const { register: registerUser, isLoading, error, clearError } = useAuthStore()
  
  const [formData, setFormData] = useState<SignupFormData>({
    firstName: '',
    lastName: '',
    email: '',
    companyName: '',
    password: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState<ValidationErrors>({})
  const [touched, setTouched] = useState<{ [key: string]: boolean }>({})
  const [passwordStrength, setPasswordStrength] = useState(0)
  const [signupSuccess, setSignupSuccess] = useState(false)
  const [showPasswordRequirements, setShowPasswordRequirements] = useState(false)

  // Real-time validation
  useEffect(() => {
    const newErrors: ValidationErrors = {}
    
    if (touched.firstName && !formData.firstName.trim()) {
      newErrors.firstName = 'Имя обязательно для заполнения'
    } else if (touched.firstName && formData.firstName.length < 2) {
      newErrors.firstName = 'Имя должно содержать минимум 2 символа'
    }
    
    if (touched.lastName && !formData.lastName.trim()) {
      newErrors.lastName = 'Фамилия обязательна для заполнения'
    } else if (touched.lastName && formData.lastName.length < 2) {
      newErrors.lastName = 'Фамилия должна содержать минимум 2 символа'
    }
    
    if (touched.email && formData.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(formData.email)) {
        newErrors.email = 'Пожалуйста, введите корректный email адрес'
      }
    }
    
    if (touched.password && formData.password) {
      if (formData.password.length < 8) {
        newErrors.password = 'Пароль должен содержать минимум 8 символов'
      } else if (passwordStrength < 3) {
        newErrors.password = 'Пароль слишком слабый - выполните все требования'
      }
    }
    
    if (touched.confirmPassword && formData.confirmPassword) {
      if (formData.password !== formData.confirmPassword) {
        newErrors.confirmPassword = 'Пароли не совпадают'
      }
    }
    
    setErrors(newErrors)
  }, [formData, touched, passwordStrength])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleBlur = (field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }))
    if (field === 'password') {
      setShowPasswordRequirements(false)
    }
  }

  const handlePasswordFocus = () => {
    setShowPasswordRequirements(true)
  }

  const getFieldSuccess = (field: keyof SignupFormData): boolean => {
    if (!touched[field] || errors[field]) return false
    
    switch (field) {
      case 'firstName':
      case 'lastName':
        return formData[field].length >= 2
      case 'email':
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData[field])
      case 'password':
        return formData[field].length >= 8 && passwordStrength >= 3
      case 'confirmPassword':
        return formData.password === formData.confirmPassword && formData.confirmPassword.length > 0
      case 'companyName':
        return true // Optional field, always success if touched
      default:
        return false
    }
  }

  const isFormValid = () => {
    return (
      formData.firstName.trim().length >= 2 &&
      formData.lastName.trim().length >= 2 &&
      /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) &&
      formData.password.length >= 8 &&
      passwordStrength >= 3 &&
      formData.password === formData.confirmPassword &&
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
    
    // Mark all required fields as touched
    setTouched({
      firstName: true,
      lastName: true,
      email: true,
      password: true,
      confirmPassword: true,
      companyName: true
    })
    
    if (!isFormValid()) {
      // Focus first invalid field for accessibility
      const firstErrorField = document.querySelector('[aria-invalid="true"]') as HTMLInputElement
      if (firstErrorField) {
        firstErrorField.focus()
      }
      return
    }
    
    const success = await registerUser({
      email: formData.email,
      password: formData.password,
      firstName: formData.firstName,
      lastName: formData.lastName,
      companyName: formData.companyName || undefined,
    })
    
    if (success) {
      setSignupSuccess(true)
      onSuccess?.()
      
      // Show success animation before redirect
      setTimeout(() => {
        router.push(redirectTo)
      }, 1500)
    }
  }

  const completedFields = Object.entries(formData).filter(([key, value]) => {
    if (key === 'companyName') return false // Optional field, don't count
    return value.trim().length > 0 && getFieldSuccess(key as keyof SignupFormData)
  }).length

  const totalRequiredFields = 5 // firstName, lastName, email, password, confirmPassword
  const progressPercentage = Math.min(100, Math.round((completedFields / totalRequiredFields) * 100))

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-400 rounded-full opacity-10 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-400 rounded-full opacity-10 blur-3xl" />
      </div>

      <Card className={cn(
        "w-full max-w-lg relative z-10 border-0 shadow-xl",
        "transition-all duration-500",
        signupSuccess && "scale-95 opacity-90"
      )}>
        <CardHeader className="space-y-1 pb-6">
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center font-bold">
            Создать аккаунт
          </CardTitle>
          <CardDescription className="text-center">
            Присоединяйтесь к XM-Port и начните управлять торговыми операциями
          </CardDescription>
          
          {/* Progress indicator */}
          {progressPercentage > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                <span>Заполнение профиля</span>
                <span>{progressPercentage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} onKeyDown={handleKeyDown} className="space-y-4" noValidate>
            {/* Name fields */}
            <div className="grid grid-cols-2 gap-3">
              <EnhancedInput
                icon={User}
                type="text"
                name="firstName"
                placeholder="Имя"
                value={formData.firstName}
                onChange={handleChange}
                onBlur={() => handleBlur('firstName')}
                error={touched.firstName ? errors.firstName : undefined}
                success={getFieldSuccess('firstName')}
                disabled={isLoading}
                required
                autoComplete="given-name"
              />
              
              <EnhancedInput
                icon={User}
                type="text"
                name="lastName"
                placeholder="Фамилия"
                value={formData.lastName}
                onChange={handleChange}
                onBlur={() => handleBlur('lastName')}
                error={touched.lastName ? errors.lastName : undefined}
                success={getFieldSuccess('lastName')}
                disabled={isLoading}
                required
                autoComplete="family-name"
              />
            </div>

            {/* Email field */}
            <EnhancedInput
              icon={Mail}
              type="email"
              name="email"
              placeholder="Email адрес"
              value={formData.email}
              onChange={handleChange}
              onBlur={() => handleBlur('email')}
              error={touched.email ? errors.email : undefined}
              success={getFieldSuccess('email')}
              disabled={isLoading}
              required
              autoComplete="email"
              helperText={!touched.email ? "Мы никогда не передадим ваш email третьим лицам" : undefined}
            />

            {/* Company field */}
            <EnhancedInput
              icon={Building}
              type="text"
              name="companyName"
              placeholder="Название компании (необязательно)"
              value={formData.companyName}
              onChange={handleChange}
              onBlur={() => handleBlur('companyName')}
              success={getFieldSuccess('companyName') && formData.companyName.length > 0}
              disabled={isLoading}
              autoComplete="organization"
              helperText={!touched.companyName ? "Поможет нам настроить ваш интерфейс" : undefined}
            />

            {/* Password field */}
            <div className="space-y-2">
              <PasswordInput
                name="password"
                placeholder="Создать пароль"
                value={formData.password}
                onChange={handleChange}
                onBlur={() => handleBlur('password')}
                onFocus={handlePasswordFocus}
                disabled={isLoading}
                required
                autoComplete="new-password"
                showStrength={formData.password.length > 0}
                showRequirements={showPasswordRequirements}
                onStrengthChange={setPasswordStrength}
              />
              {errors.password && touched.password && (
                <p className="text-sm text-red-600 animate-in fade-in-50 slide-in-from-top-1">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Confirm password field */}
            <EnhancedInput
              type="password"
              name="confirmPassword"
              placeholder="Подтвердить пароль"
              value={formData.confirmPassword}
              onChange={handleChange}
              onBlur={() => handleBlur('confirmPassword')}
              error={touched.confirmPassword ? errors.confirmPassword : undefined}
              success={getFieldSuccess('confirmPassword')}
              disabled={isLoading}
              required
              autoComplete="new-password"
            />

            {/* API Error */}
            {error && (
              <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3 animate-in fade-in-50 slide-in-from-top-1">
                {error}
              </div>
            )}

            {/* Submit button */}
            <Button
              type="submit"
              disabled={!isFormValid() || isLoading}
              className={cn(
                "w-full h-11 font-medium transition-all duration-300 mt-6",
                "bg-gradient-to-r from-blue-600 to-purple-600",
                "hover:from-blue-700 hover:to-purple-700",
                "disabled:from-gray-300 disabled:to-gray-400",
                "shadow-lg hover:shadow-xl hover:-translate-y-0.5",
                signupSuccess && "from-green-500 to-green-600"
              )}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Создание аккаунта...
                </>
              ) : signupSuccess ? (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Аккаунт создан!
                </>
              ) : (
                <>
                  Создать аккаунт
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>

            {/* Social login divider */}
            <div className="relative py-3">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-4 text-gray-500">Или зарегистрируйтесь через</span>
              </div>
            </div>

            {/* Social login buttons */}
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

          {/* Sign in link */}
          <p className="text-center text-sm text-gray-600 mt-6">
            Уже есть аккаунт?{' '}
            <Link
              href="/auth/login"
              className="font-medium text-blue-600 hover:text-blue-700 hover:underline transition-colors"
            >
              Войти
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}