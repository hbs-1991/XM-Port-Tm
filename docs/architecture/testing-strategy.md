# Testing Strategy

## Testing Pyramid

```
        E2E Tests
       /        \
   Integration Tests
  /            \
Frontend Unit  Backend Unit
```

## Test Organization

### Frontend Tests
```
apps/web/tests/
├── components/           # Component unit tests
│   ├── landing/
│   ├── dashboard/
│   └── admin/
├── hooks/               # Custom hooks tests
├── services/            # API client tests
├── utils/               # Utility function tests
└── e2e/                 # End-to-end tests
    ├── auth.spec.ts
    ├── file-processing.spec.ts
    └── admin.spec.ts
```

### Backend Tests
```
apps/api/tests/
├── unit/                # Unit tests
│   ├── services/
│   ├── repositories/
│   └── utils/
├── integration/         # Integration tests
│   ├── api/
│   ├── database/
│   └── external_apis/
└── fixtures/            # Test data
    ├── users.py
    ├── processing_jobs.py
    └── hs_codes.py
```

## Test Examples

### Frontend Component Test
```typescript
// apps/web/tests/components/dashboard/FileUpload.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileUpload } from '@/components/dashboard/FileUpload';
import { useAuthStore } from '@/stores/auth';

jest.mock('@/stores/auth');

describe('FileUpload Component', () => {
  beforeEach(() => {
    (useAuthStore as jest.Mock).mockReturnValue({
      user: { id: '1', creditsRemaining: 10 },
      isAuthenticated: true,
    });
  });

  it('should upload file successfully', async () => {
    const mockOnUpload = jest.fn();
    render(<FileUpload onUpload={mockOnUpload} />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const file = new File(['test content'], 'test.csv', { type: 'text/csv' });

    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByText(/process file/i));

    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(file);
    });
  });

  it('should show error for insufficient credits', async () => {
    (useAuthStore as jest.Mock).mockReturnValue({
      user: { id: '1', creditsRemaining: 0 },
      isAuthenticated: true,
    });

    render(<FileUpload />);
    
    expect(screen.getByText(/insufficient credits/i)).toBeInTheDocument();
  });
});
```

### Backend API Test
```python