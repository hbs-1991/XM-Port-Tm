/**
 * Authentication API client service
 */

interface LoginCredentials {
  email: string
  password: string
}

interface RegisterData {
  email: string
  password: string
  first_name: string
  last_name: string
  company_name?: string
}

interface AuthResponse {
  user: {
    id: string
    email: string
    first_name: string
    last_name: string
    role: string
    company_name?: string
    is_active: boolean
  }
  tokens: {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
  }
}

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class AuthService {
  private baseUrl = `${API_BASE_URL}/api/v1/auth`

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await fetch(`${this.baseUrl}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    return response.json()
  }

  async register(userData: RegisterData): Promise<AuthResponse> {
    const response = await fetch(`${this.baseUrl}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    return response.json()
  }

  async logout(accessToken: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Logout failed')
    }
  }

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await fetch(`${this.baseUrl}/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Token refresh failed')
    }

    return response.json()
  }

  async requestPasswordReset(email: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/password-reset-request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Password reset request failed')
    }
  }

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/password-reset-confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token,
        new_password: newPassword,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Password reset failed')
    }
  }
}

export const authService = new AuthService()
export type { LoginCredentials, RegisterData, AuthResponse, TokenResponse }