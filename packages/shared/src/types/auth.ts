/**
 * Authentication-related type definitions
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  companyName?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: string;
    companyName?: string;
    isActive: boolean;
  };
  tokens: TokenResponse;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface PasswordResetResponse {
  message: string;
}

export interface LogoutResponse {
  message: string;
}

export interface JWTPayload {
  sub: string;
  email?: string;
  role?: string;
  type: 'access' | 'refresh' | 'password_reset';
  exp: number;
  iat: number;
  jti?: string;
}

export interface AuthError {
  detail: string;
  status_code: number;
}