/**
 * NextAuth.js type extensions for XM-Port
 */
import 'next-auth'
import 'next-auth/jwt'
import type { User as SharedUser } from '@xm-port/shared'

declare module 'next-auth' {
  interface Session {
    user: SharedUser & {
      accessToken: string
      refreshToken: string
    }
    accessToken: string
    refreshToken: string
  }

  interface User extends SharedUser {
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