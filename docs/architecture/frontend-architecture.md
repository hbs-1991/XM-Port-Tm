# Frontend Architecture

## Route Structure & Organization
```typescript
app/
├── (public)/                    # Public marketing routes
│   ├── page.tsx                 # Home page (/)
│   ├── features/                # Features page (/features)
│   ├── pricing/                 # Pricing page (/pricing) 
│   ├── about/                   # About page (/about)
│   ├── contact/                 # Contact page (/contact)
│   ├── demo/                    # Demo/trial page (/demo)
│   ├── blog/                    # Blog section (/blog)
│   └── layout.tsx               # Public layout with marketing nav
├── (dashboard)/                 # Protected application routes
│   ├── dashboard/               # Main dashboard (/dashboard)
│   ├── upload/                  # File upload (/upload)
│   ├── history/                 # Processing history (/history)
│   └── layout.tsx               # Dashboard layout with app nav
├── (admin)/                     # Admin panel routes (Role: PROJECT_OWNER)
│   ├── admin/                   # Admin dashboard overview
│   ├── analytics/               # User analytics
│   ├── settings/                # System settings
│   └── layout.tsx               # Admin layout with admin nav
└── api/                         # Shared API routes
    ├── auth/                    # Authentication endpoints
    ├── contact/                 # Contact form handler
    └── newsletter/              # Newsletter signup
```

## Component Architecture

```typescript
components/
├── landing/
│   ├── hero/
│   │   ├── HeroSection.tsx      # Main hero with CTA
│   │   ├── HeroVideo.tsx        # Product demo video
│   │   └── HeroStats.tsx        # Key metrics display
│   ├── features/
│   │   ├── FeatureGrid.tsx      # Feature overview grid
│   │   ├── AIProcessingDemo.tsx # Interactive AI demo
│   │   └── TimeComparison.tsx   # Before/after time savings
│   ├── pricing/
│   │   ├── PricingTiers.tsx     # Credit-based pricing
│   │   ├── ROICalculator.tsx    # Custom ROI calculator
│   │   └── ComparisonTable.tsx  # Feature comparison
│   └── conversion/
│       ├── CTASection.tsx       # Call-to-action sections
│       ├── DemoRequest.tsx      # Demo request form
│       └── TrialSignup.tsx      # Free trial signup
├── dashboard/
│   ├── upload/
│   │   ├── FileUpload.tsx       # Drag & drop file upload
│   │   ├── ProcessingProgress.tsx # Real-time progress
│   │   └── ResultsTable.tsx     # Processing results
│   ├── history/
│   │   ├── JobHistory.tsx       # Processing job history
│   │   └── JobDetails.tsx       # Individual job details
│   └── analytics/
│       ├── UsageMetrics.tsx     # User usage analytics
│       └── CreditBalance.tsx    # Credit balance display
├── admin/
│   ├── analytics/
│   │   ├── UserAnalytics.tsx    # User behavior analytics
│   │   ├── SystemHealth.tsx     # System performance dashboard
│   │   └── RealTimeMetrics.tsx  # Live system metrics
│   ├── user-management/
│   │   ├── UserTable.tsx        # User management table
│   │   └── CreditManagement.tsx # Credit allocation/adjustment
│   └── charts/
│       ├── LineChart.tsx        # Time series charts
│       ├── BarChart.tsx         # Comparison charts
│       └── PieChart.tsx         # Distribution charts
└── shared/                      # Shared between all sections
    ├── auth/
    │   ├── LoginForm.tsx
    │   ├── SignupForm.tsx
    │   └── AuthModal.tsx
    ├── ui/                      # shadcn/ui components
    │   ├── button.tsx
    │   ├── input.tsx
    │   ├── card.tsx
    │   └── ...
    └── navigation/
        ├── Header.tsx
        ├── Footer.tsx
        └── Sidebar.tsx
```

## State Management Architecture

```typescript
// Global auth state with Zustand
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  login: async (email, password) => {
    const response = await authApi.login({ email, password });
    set({ user: response.user, isAuthenticated: true });
  },
  logout: () => {
    set({ user: null, isAuthenticated: false });
    // Clear tokens from storage
  },
  refreshToken: async () => {
    // Token refresh logic
  }
}));

// Server state with React Query
export const useProcessingJobs = (filters?: JobFilters) => {
  return useQuery({
    queryKey: ['processing-jobs', filters],
    queryFn: () => processingApi.getJobs(filters),
    staleTime: 30000, // 30 seconds
  });
};

// Real-time WebSocket integration
export const useProcessingUpdates = (jobId: string) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<JobStatus>('PENDING');

  useEffect(() => {
    const ws = new WebSocket(`/ws/processing?token=${getAuthToken()}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.jobId === jobId) {
        setProgress(data.progress);
        setStatus(data.status);
      }
    };

    return () => ws.close();
  }, [jobId]);

  return { progress, status };
};
```
