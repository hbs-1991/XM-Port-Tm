# Coding Standards

## Critical Fullstack Rules

- **Type Sharing:** Always define types in packages/shared and import from there - ensures consistency between frontend and backend
- **API Calls:** Never make direct HTTP calls from components - use the service layer for proper error handling and caching
- **Environment Variables:** Access only through config objects, never process.env directly - enables proper validation and type safety
- **Error Handling:** All API routes must use the standard error handler - ensures consistent error format across the system
- **State Updates:** Never mutate state directly - use proper state management patterns (Zustand actions, React Query mutations)
- **Database Transactions:** Always use transactions for multi-table operations - prevents data inconsistency
- **Credit Deduction:** Must be atomic and check balance before processing - prevents race conditions and overselling
- **File Upload Validation:** Validate file type, size, and structure before processing - prevents system abuse and errors

## Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `UserProfile.tsx` |
| Hooks | camelCase with 'use' | - | `useAuth.ts` |
| API Routes | - | kebab-case | `/api/user-profile` |
| Database Tables | - | snake_case | `user_profiles` |
| Functions | camelCase | snake_case | `getUserData()`, `get_user_data()` |
| Constants | SCREAMING_SNAKE_CASE | SCREAMING_SNAKE_CASE | `MAX_FILE_SIZE` |
