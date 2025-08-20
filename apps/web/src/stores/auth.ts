/**
 * Authentication state management with Zustand
 */
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { signIn, signOut, getSession } from 'next-auth/react'
import type { Session } from 'next-auth'

interface User {
  id: string
  email: string
  name: string
  role: string
}

interface AuthState {
  user: User | null
  session: Session | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (email: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
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
        set({ isLoading: true })
        
        try {
          await signOut({ redirect: false })
          set({ 
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          })
        } catch (error) {
          set({ 
            error: 'Logout failed', 
            isLoading: false 
          })
        }
      },

      refreshSession: async () => {
        try {
          const session = await getSession()
          if (session?.user) {
            set({
              session,
              user: {
                id: session.user.id,
                email: session.user.email,
                name: session.user.name || '',
                role: session.user.role,
              },
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
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: userData.email,
              password: userData.password,
              first_name: userData.firstName,
              last_name: userData.lastName,
              company_name: userData.companyName,
            }),
          })

          if (!response.ok) {
            const errorData = await response.json()
            set({ 
              error: errorData.detail || 'Registration failed', 
              isLoading: false 
            })
            return false
          }

          // Auto-login after successful registration
          const success = await get().login(userData.email, userData.password)
          set({ isLoading: false })
          return success
        } catch (error) {
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
            user: {
              id: session.user.id,
              email: session.user.email,
              name: session.user.name || '',
              role: session.user.role,
            },
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