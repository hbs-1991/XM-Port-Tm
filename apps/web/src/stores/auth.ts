/**
 * Authentication state management with Zustand
 */
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { signIn, signOut, getSession } from 'next-auth/react'
import type { Session } from 'next-auth'
import type { User } from '@xm-port/shared'
import { authService } from '@/services/auth'

interface AuthState {
  user: User | null
  session: Session | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (email: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
  logoutAll: () => Promise<void>
  refreshSession: () => Promise<void>
  register: (userData: RegisterData) => Promise<boolean>
  clearError: () => void
  setSession: (session: Session | null) => void
}

interface RegisterData {
  email: string
  password: string
  firstName: string
  lastName: string
  companyName?: string
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => ({
      user: null,
      session: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const result = await signIn('credentials', {
            email,
            password,
            redirect: false,
          })

          if (result?.error) {
            set({ error: 'Invalid email or password', isLoading: false })
            return false
          }

          // Refresh session after successful login
          await get().refreshSession()
          set({ isLoading: false })
          return true
        } catch (error) {
          set({ 
            error: 'Login failed. Please try again.', 
            isLoading: false 
          })
          return false
        }
      },

      logout: async () => {
        set({ isLoading: true, error: null })
        
        try {
          const currentSession = get().session
          
          // Call backend logout API if we have a valid session with tokens
          if (currentSession?.accessToken) {
            try {
              await authService.logout(
                currentSession.accessToken,
                currentSession.refreshToken
              )
            } catch (apiError) {
              // Log API error but don't fail the logout - we'll still clear client-side state
              console.warn('Backend logout failed, proceeding with client-side cleanup:', apiError)
            }
          }

          // Clear NextAuth session (this also triggers the signOut event we configured)
          await signOut({ redirect: false })
          
          // Clear all client-side state
          set({ 
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          })
        } catch (error) {
          console.error('Logout error:', error)
          // Even if logout fails, clear the client state
          set({ 
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            error: 'Logout failed, but session cleared'
          })
        }
      },

      logoutAll: async () => {
        set({ isLoading: true, error: null })
        
        try {
          const currentSession = get().session
          
          // Call backend logout-all API if we have a valid session
          if (currentSession?.accessToken) {
            try {
              await authService.logoutAll(currentSession.accessToken)
            } catch (apiError) {
              console.warn('Backend logout all failed, proceeding with client-side cleanup:', apiError)
            }
          }

          // Clear NextAuth session and all client-side state
          await signOut({ redirect: false })
          
          // Clear all client-side state
          set({ 
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          })
        } catch (error) {
          console.error('Logout all error:', error)
          // Even if logout fails, clear the client state
          set({ 
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            error: 'Logout from all devices failed, but session cleared'
          })
        }
      },

      refreshSession: async () => {
        try {
          const session = await getSession()
          if (session?.user) {
            set({
              session,
              user: session.user as User,
              isAuthenticated: true,
            })
          } else {
            set({
              session: null,
              user: null,
              isAuthenticated: false,
            })
          }
        } catch (error) {
          console.error('Failed to refresh session:', error)
          set({
            session: null,
            user: null,
            isAuthenticated: false,
          })
        }
      },

      register: async (userData: RegisterData) => {
        set({ isLoading: true, error: null })
        
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          
          // DEBUG: Log API request details
          const requestBody = {
            email: userData.email,
            password: userData.password,
            first_name: userData.firstName,
            last_name: userData.lastName,
            company_name: userData.companyName,
          }
          console.log('=== API REQUEST DEBUG ===')
          console.log('API URL:', `${apiUrl}/api/v1/auth/register`)
          console.log('Request Body:', requestBody)
          console.log('Request Headers:', { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          })
          
          const response = await fetch(`${apiUrl}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify(requestBody),
          })

          // DEBUG: Log response details
          console.log('=== API RESPONSE DEBUG ===')
          console.log('Response Status:', response.status)
          console.log('Response Headers:', Object.fromEntries(response.headers.entries()))
          
          if (!response.ok) {
            const errorData = await response.json()
            console.log('Error Response Body:', errorData)
            console.log('Detailed Error:', {
              status: response.status,
              statusText: response.statusText,
              errorDetail: errorData.detail,
              fullError: errorData
            })
            set({ 
              error: errorData.detail || 'Registration failed', 
              isLoading: false 
            })
            return false
          }

          const successData = await response.json()
          console.log('Success Response Body:', successData)
          console.log('Registration successful! User created:', successData.user)

          // Auto-login after successful registration
          const success = await get().login(userData.email, userData.password)
          set({ isLoading: false })
          return success
        } catch (error) {
          console.log('=== CATCH ERROR DEBUG ===')
          console.error('Registration network/parsing error:', error)
          console.log('Error type:', typeof error)
          console.log('Error message:', error instanceof Error ? error.message : 'Unknown error')
          set({ 
            error: 'Registration failed. Please try again.', 
            isLoading: false 
          })
          return false
        }
      },

      clearError: () => set({ error: null }),
      
      setSession: (session: Session | null) => {
        if (session?.user) {
          set({
            session,
            user: session.user as User,
            isAuthenticated: true,
          })
        } else {
          set({
            session: null,
            user: null,
            isAuthenticated: false,
          })
        }
      },
    }),
    {
      name: 'auth-store',
    }
  )
)