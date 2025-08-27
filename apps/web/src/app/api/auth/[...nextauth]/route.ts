/**
 * NextAuth.js configuration for XM-Port authentication
 */
import NextAuth from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import type { NextAuthOptions } from 'next-auth'
import { UserRole } from '@xm-port/shared'

const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'email@example.com' },
        password: { label: 'Password', type: 'password' }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }

        try {
          // Call our backend API for authentication
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          })

          if (!response.ok) {
            return null
          }

          const data = await response.json()

          // Return user object with tokens and complete user data
          return {
            id: data.user.id,
            email: data.user.email,
            hashedPassword: '', // Don't expose password
            firstName: data.user.first_name,
            lastName: data.user.last_name,
            role: data.user.role,
            subscriptionTier: data.user.subscription_tier,
            creditsRemaining: data.user.credits_remaining,
            creditsUsedThisMonth: data.user.credits_used_this_month,
            companyName: data.user.company_name,
            country: data.user.country,
            createdAt: new Date(data.user.created_at),
            lastLoginAt: data.user.last_login_at ? new Date(data.user.last_login_at) : undefined,
            isActive: data.user.is_active,
            accessToken: data.tokens.access_token,
            refreshToken: data.tokens.refresh_token,
          }
        } catch (error) {
          console.error('Authentication error:', error)
          return null
        }
      }
    })
  ],
  session: {
    strategy: 'jwt',
    maxAge: 15 * 60, // 15 minutes (matches backend access token expiry)
  },
  cookies: {
    sessionToken: {
      name: 'next-auth.session-token',
      options: {
        httpOnly: true,
        sameSite: 'strict',
        path: '/',
        secure: true, // Always use secure cookies
        maxAge: 15 * 60, // 15 minutes
      }
    },
    callbackUrl: {
      name: 'next-auth.callback-url',
      options: {
        httpOnly: true,
        sameSite: 'strict',
        path: '/',
        secure: true, // Always use secure cookies
      }
    },
    csrfToken: {
      name: 'next-auth.csrf-token',
      options: {
        httpOnly: true,
        sameSite: 'strict',
        path: '/',
        secure: true, // Always use secure cookies
      }
    }
  },
  callbacks: {
    async jwt({ token, user, account }) {
      // Persist tokens and user info in JWT
      if (account && user) {
        const extendedUser = user as any
        token.accessToken = extendedUser.accessToken
        token.refreshToken = extendedUser.refreshToken
        token.role = extendedUser.role
        token.userId = extendedUser.id
        token.accessTokenExpires = Math.floor(Date.now() / 1000) + (15 * 60) // 15 minutes
      }

      // Check if access token needs refresh (within 2 minutes of expiry)
      const now = Math.floor(Date.now() / 1000)
      if (token.accessTokenExpires && now > token.accessTokenExpires - 120) {
        try {
          const refreshedTokens = await refreshAccessToken(token.refreshToken as string)
          if (refreshedTokens) {
            token.accessToken = refreshedTokens.access_token
            token.refreshToken = refreshedTokens.refresh_token
            token.accessTokenExpires = now + (15 * 60) // 15 minutes
          } else {
            // If refresh fails, clear all token data to force re-authentication
            return {}
          }
        } catch (error) {
          console.error('Token refresh failed:', error)
          // Clear all token data to force re-authentication
          return {}
        }
      }

      return token
    },
    async session({ session, token }) {
      // Check if we have valid token data
      if (!token.userId || !token.accessToken) {
        // If token is invalid or missing, return null to force re-authentication
        return null
      }

      // Send properties to the client
      session.user.id = token.userId as string
      session.user.role = token.role as UserRole
      session.accessToken = token.accessToken as string
      session.refreshToken = token.refreshToken as string
      
      // Fetch full user data for session
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/v1/users/profile`, {
          headers: {
            'Authorization': `Bearer ${token.accessToken}`,
          },
        })
        
        if (response.ok) {
          const userData = await response.json()
          session.user = {
            ...session.user,
            ...userData,
            accessToken: token.accessToken as string,
            refreshToken: token.refreshToken as string,
          }
        } else if (response.status === 401 || response.status === 404) {
          // User no longer exists or token is invalid
          console.log('User profile fetch failed, forcing re-authentication')
          return null
        }
      } catch (error) {
        console.error('Failed to fetch user profile:', error)
        // On fetch error, return null to force re-authentication
        return null
      }
      
      return session
    }
  },
  pages: {
    signIn: '/auth/login',
    error: '/auth/error',
  },
  events: {
    async signOut({ token }) {
      // Clean up refresh tokens when user signs out
      if (token?.userId && token?.refreshToken) {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          await fetch(`${apiUrl}/api/v1/auth/logout`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token.accessToken}`,
            },
          })
        } catch (error) {
          console.error('Error during logout cleanup:', error)
        }
      }
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
}

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken(refreshToken: string) {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    })

    if (!response.ok) {
      if (response.status === 401) {
        console.log('Refresh token is invalid or expired')
      } else if (response.status === 404) {
        console.log('User not found during token refresh')
      } else {
        console.error(`Token refresh failed with status ${response.status}`)
      }
      return null
    }

    const tokens = await response.json()
    return tokens
  } catch (error) {
    console.error('Error refreshing token:', error)
    return null
  }
}

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }