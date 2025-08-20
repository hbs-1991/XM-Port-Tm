# Database Schema

## Core Tables with Optimizations

```sql
-- Users table with indexing for authentication and analytics
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER' 
        CHECK (role IN ('USER', 'ADMIN', 'PROJECT_OWNER')),
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'FREE'
        CHECK (subscription_tier IN ('FREE', 'BASIC', 'PREMIUM', 'ENTERPRISE')),
    credits_remaining INTEGER NOT NULL DEFAULT 2,
    credits_used_this_month INTEGER NOT NULL DEFAULT 0,
    company VARCHAR(255),
    country VARCHAR(3) NOT NULL, -- ISO 3166-1 alpha-3
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Performance indexes
    CONSTRAINT positive_credits CHECK (credits_remaining >= 0)
);

-- Indexes for user queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_country ON users(country);
CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX idx_users_created_at ON users(created_at);

-- HS Codes table with pgvector for AI similarity search
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE hs_codes (
    code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    chapter VARCHAR(2) NOT NULL,
    section VARCHAR(2) NOT NULL,
    embedding vector(1536), -- OpenAI embedding size
    country VARCHAR(3) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Vector similarity search indexes (HNSW for performance)
CREATE INDEX ON hs_codes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON hs_codes USING hnsw (embedding vector_l2_ops);
CREATE INDEX idx_hs_codes_country_active ON hs_codes(country, is_active) WHERE is_active = true;

-- Processing jobs with partitioning for performance
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    input_file_name VARCHAR(255) NOT NULL,
    input_file_url TEXT NOT NULL,
    input_file_size BIGINT NOT NULL,
    output_xml_url TEXT,
    credits_used INTEGER NOT NULL DEFAULT 0,
    processing_time_ms INTEGER,
    total_products INTEGER DEFAULT 0,
    successful_matches INTEGER DEFAULT 0,
    average_confidence DECIMAL(3,2),
    country_schema VARCHAR(3) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT positive_file_size CHECK (input_file_size > 0),
    CONSTRAINT valid_confidence CHECK (average_confidence BETWEEN 0 AND 1),
    CONSTRAINT positive_credits CHECK (credits_used >= 0)
) PARTITION BY RANGE (created_at);

-- Monthly partitions for performance
CREATE TABLE processing_jobs_2024_01 PARTITION OF processing_jobs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Indexes for processing jobs
CREATE INDEX idx_processing_jobs_user_created ON processing_jobs(user_id, created_at DESC);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_country ON processing_jobs(country_schema);
```
