/**
 * User-related type definitions
 */

export interface User {
  id: string;
  email: string;
  hashedPassword: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  subscriptionTier: SubscriptionTier;
  creditsRemaining: number;
  creditsUsedThisMonth: number;
  companyName?: string;
  country: string;
  createdAt: Date;
  lastLoginAt?: Date;
  isActive: boolean;
}

export enum UserRole {
  USER = 'USER',
  ADMIN = 'ADMIN',
  PROJECT_OWNER = 'PROJECT_OWNER'
}

export enum SubscriptionTier {
  FREE = 'FREE',
  BASIC = 'BASIC',
  PREMIUM = 'PREMIUM',
  ENTERPRISE = 'ENTERPRISE'
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
  firstName: string;
  lastName: string;
  companyName?: string;
}

export interface BillingTransaction {
  id: string;
  userId: string;
  type: BillingTransactionType;
  amount: number;
  currency: string;
  creditsGranted: number;
  paymentProvider: string;
  paymentId: string;
  status: BillingTransactionStatus;
  createdAt: Date;
}

export enum BillingTransactionType {
  CREDIT_PURCHASE = 'CREDIT_PURCHASE',
  SUBSCRIPTION = 'SUBSCRIPTION',
  REFUND = 'REFUND'
}

export enum BillingTransactionStatus {
  PENDING = 'PENDING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  REFUNDED = 'REFUNDED'
}