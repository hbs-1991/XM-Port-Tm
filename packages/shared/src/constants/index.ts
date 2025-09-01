/**
 * Shared constants across the application
 */

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    LOGOUT: '/api/v1/auth/logout',
    REGISTER: '/api/v1/auth/register',
  },
  PROCESSING: {
    UPLOAD: '/api/v1/processing/upload',
    JOBS: '/api/v1/processing/jobs',
  },
  ADMIN: {
    USERS: '/api/v1/admin/users',
    ANALYTICS: '/api/v1/admin/analytics',
  },
} as const;

export const FILE_CONSTRAINTS = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_EXTENSIONS: ['.pdf', '.xlsx', '.xls', '.csv'] as const,
  ALLOWED_MIME_TYPES: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
  ] as const,
} as const;

export const PROCESSING_LIMITS = {
  MAX_CONCURRENT_JOBS: 5,
  DEFAULT_TIMEOUT: 300000, // 5 minutes
  RETRY_ATTEMPTS: 3,
} as const;