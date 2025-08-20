/**
 * NextAuth.js configuration for XM-Port authentication
 */
import NextAuth from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import type { NextAuthOptions } from 'next-auth'

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
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login`, {
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

          // Return user object with tokens
          return {
            id: data.user.id,
            email: data.user.email,
            name: `${data.user.first_name} ${data.user.last_name}`,
            role: data.user.role,
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
        secure: process.env.NODE_ENV === 'production',
        maxAge: 15 * 60, // 15 minutes
      }
    },
    callbackUrl: {
      name: 'next-auth.callback-url',
      options: {
        httpOnly: true,
        sameSite: 'strict',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      }
    },
    csrfToken: {
      name: 'next-auth.csrf-token',
      options: {
        httpOnly: true,
        sameSite: 'strict',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      }
    }
  },
  callbacks: {
    async jwt({ token, user, account }) {
      // Persist tokens and user info in JWT
      if (account && user) {
        token.accessToken = user.accessToken
        token.refreshToken = user.refreshToken
        token.role = user.role
        token.userId = user.id
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
          }
        } catch (error) {
          console.error('Token refresh failed:', error)
          // Force re-login by returning empty token
          return {}
        }
      }

      return token
    },
    async session({ session, token }) {
      // Send properties to the client
      session.user.id = token.userId as string
      session.user.role = token.role as string
      session.accessToken = token.accessToken as string
      session.refreshToken = token.refreshToken as string
      return session
    }
  },
  pages: {
    signIn: '/auth/login',
    signUp: '/auth/register',
    error: '/auth/error',
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
}

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken(refreshToken: string) {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to refresh token')
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