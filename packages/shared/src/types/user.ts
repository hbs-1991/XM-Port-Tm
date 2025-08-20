/**
 * User-related type definitions
 */

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  credits: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  SUPER_ADMIN = 'super_admin'
}

export interface UserSession {
  user: User;
  accessToken: string;
  refreshToken?: string;
  expiresAt: Date;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}