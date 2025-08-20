# Data Models

## User

**Purpose:** Represents customs brokers using the system, including authentication, subscription, and usage tracking.

**Key Attributes:**
- id: UUID - Unique user identifier
- email: string - Primary authentication and communication
- hashedPassword: string - Secure password storage
- role: enum ['USER', 'ADMIN', 'PROJECT_OWNER'] - Role-based access control
- subscriptionTier: enum ['FREE', 'BASIC', 'PREMIUM', 'ENTERPRISE'] - Billing tier
- creditsRemaining: number - Available processing credits
- creditsUsedThisMonth: number - Monthly usage tracking
- company: string - Brokerage firm name
- country: string - Operating country (for schema selection)
- createdAt: DateTime - Registration timestamp
- lastLoginAt: DateTime - Activity tracking
- isActive: boolean - Account status

### TypeScript Interface
```typescript
interface User {
  id: string;
  email: string;
  hashedPassword: string;
  role: 'USER' | 'ADMIN' | 'PROJECT_OWNER';
  subscriptionTier: 'FREE' | 'BASIC' | 'PREMIUM' | 'ENTERPRISE';
  creditsRemaining: number;
  creditsUsedThisMonth: number;
  company: string;
  country: string;
  createdAt: Date;
  lastLoginAt: Date | null;
  isActive: boolean;
}
```

### Relationships
- One-to-many with ProcessingJob
- One-to-many with BillingTransaction
- One-to-many with UserActivity

## ProcessingJob

**Purpose:** Represents a file processing request from CSV/XLSX upload through AI processing to XML output.

**Key Attributes:**
- id: UUID - Unique job identifier
- userId: UUID - Owner reference
- status: enum - Current processing state
- inputFileName: string - Original file name
- inputFileUrl: string - S3 storage URL
- inputFileSize: number - File size in bytes
- outputXmlUrl: string - Generated XML location
- creditsUsed: number - Processing cost
- processingTimeMs: number - Performance tracking
- totalProducts: number - Products processed
- successfulMatches: number - Successful HS code matches
- averageConfidence: number - AI matching confidence
- countrySchema: string - Target country for XML generation
- errorMessage: string - Failure details
- createdAt: DateTime - Job submission
- startedAt: DateTime - Processing start
- completedAt: DateTime - Processing end

### TypeScript Interface
```typescript
interface ProcessingJob {
  id: string;
  userId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  inputFileName: string;
  inputFileUrl: string;
  inputFileSize: number;
  outputXmlUrl: string | null;
  creditsUsed: number;
  processingTimeMs: number | null;
  totalProducts: number;
  successfulMatches: number;
  averageConfidence: number;
  countrySchema: string;
  errorMessage: string | null;
  createdAt: Date;
  startedAt: Date | null;
  completedAt: Date | null;
}
```

### Relationships
- Many-to-one with User
- One-to-many with ProductMatch

## ProductMatch

**Purpose:** Individual product-to-HS code matching results within a processing job.

**Key Attributes:**
- id: UUID - Unique match identifier
- jobId: UUID - Parent processing job
- productDescription: string - Original product description
- quantity: number - Product quantity
- unitOfMeasure: string - Unit type
- value: number - Declared value
- originCountry: string - Country of origin
- matchedHSCode: string - AI-selected HS code
- confidenceScore: number - AI confidence (0-1)
- alternativeHSCodes: string[] - Other possible matches
- requiresManualReview: boolean - Low confidence flag
- userConfirmed: boolean - User validation status
- createdAt: DateTime - Match timestamp

### TypeScript Interface
```typescript
interface ProductMatch {
  id: string;
  jobId: string;
  productDescription: string;
  quantity: number;
  unitOfMeasure: string;
  value: number;
  originCountry: string;
  matchedHSCode: string;
  confidenceScore: number;
  alternativeHSCodes: string[];
  requiresManualReview: boolean;
  userConfirmed: boolean;
  createdAt: Date;
}
```

### Relationships
- Many-to-one with ProcessingJob
- Many-to-one with HSCode (via matchedHSCode)

## HSCode

**Purpose:** Harmonized System codes database with AI embeddings for similarity search.

**Key Attributes:**
- code: string - HS code (primary key)
- description: string - Official description
- chapter: string - HS chapter classification
- section: string - HS section classification
- embedding: vector - OpenAI embedding for similarity
- country: string - Country-specific variations
- isActive: boolean - Current validity
- updatedAt: DateTime - Last update timestamp

### TypeScript Interface
```typescript
interface HSCode {
  code: string;
  description: string;
  chapter: string;
  section: string;
  embedding: number[]; // Vector embedding
  country: string;
  isActive: boolean;
  updatedAt: Date;
}
```

### Relationships
- One-to-many with ProductMatch

## BillingTransaction

**Purpose:** Credit purchases and subscription payments tracking.

**Key Attributes:**
- id: UUID - Transaction identifier
- userId: UUID - Customer reference
- type: enum - Transaction type
- amount: number - Payment amount
- currency: string - Payment currency
- creditsGranted: number - Credits added to account
- paymentProvider: string - Payment processor
- paymentId: string - External payment reference
- status: enum - Transaction status
- createdAt: DateTime - Transaction timestamp

### TypeScript Interface
```typescript
interface BillingTransaction {
  id: string;
  userId: string;
  type: 'CREDIT_PURCHASE' | 'SUBSCRIPTION' | 'REFUND';
  amount: number;
  currency: string;
  creditsGranted: number;
  paymentProvider: string;
  paymentId: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'REFUNDED';
  createdAt: Date;
}
```

### Relationships
- Many-to-one with User
