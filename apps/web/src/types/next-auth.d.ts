/**
 * NextAuth.js type extensions for XM-Port
 */
import 'next-auth'
import 'next-auth/jwt'

declare module 'next-auth' {
  interface Session {
    user: {
      id: string
      email: string
      name: string
      role: string
    }
    accessToken: string
    refreshToken: string
  }

  interface User {
    id: string
    email: string
    name: string
    role: string
    accessToken: string
    refreshToken: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    userId: string
    role: string
    accessToken: string
    refreshToken: string
    accessTokenExpires: number
  }
}