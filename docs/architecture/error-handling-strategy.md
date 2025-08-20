# Error Handling Strategy

## Error Flow

```mermaid
sequenceDiagram
    participant Client as Frontend
    participant API as FastAPI
    participant Service as Service Layer
    participant DB as Database
    participant External as External API

    Client->>API: Request with invalid data
    API->>API: Pydantic validation error
    API-->>Client: 400 Bad Request + details
    
    Client->>API: Valid request
    API->>Service: Process request
    Service->>DB: Database operation
    DB-->>Service: Database error
    Service->>Service: Log error + context
    Service-->>API: Service error
    API->>API: Format error response
    API-->>Client: 500 Internal Server Error
    
    Service->>External: External API call
    External-->>Service: Rate limit error
    Service->>Service: Circuit breaker logic
    Service->>Service: Fallback strategy
    Service-->>API: Success with fallback
    API-->>Client: 200 OK + fallback notice
```

## Error Response Format

```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId: string;
  };
}
```

## Frontend Error Handling

```typescript
// Global error handling with React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      onError: (error: any) => {
        // Global error handling
        if (error?.response?.status === 401) {
          // Redirect to login
          window.location.href = '/auth/login';
        } else if (error?.response?.status === 402) {
          // Show credit purchase modal
          showCreditPurchaseModal();
        } else {
          // Show generic error toast
          toast.error(error?.response?.data?.error?.message || 'An error occurred');
        }
      },
    },
  },
});

// Service layer error handling
class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiClient = {
  async request<T>(url: string, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new ApiError(
          response.status,
          errorData.error?.code || 'UNKNOWN_ERROR',
          errorData.error?.message || 'An error occurred',
          errorData.error?.details
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      // Network or other errors
      throw new ApiError(500, 'NETWORK_ERROR', 'Network error occurred');
    }
  },
};
```

## Backend Error Handling

```python