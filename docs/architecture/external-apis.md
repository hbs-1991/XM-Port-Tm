# External APIs

## OpenAI Agents SDK API

- **Purpose:** AI-powered HS code matching using production-ready agent orchestration with FileSearchTool for vector store queries
- **Documentation:** https://github.com/openai/openai-agents-python
- **Base URL(s):** https://api.openai.com/v1 (via OpenAI Agents SDK)
- **Authentication:** Bearer token (OpenAI API key)
- **Rate Limits:** Tier 3: 5,000 RPM, 160,000 TPM

**Key Endpoints Used:**
- Agent execution via `Runner.run()` - AI processing orchestration
- FileSearchTool vector store queries - HS code similarity search
- Vector store management - Embedding storage and retrieval

**Integration Notes:** 
- Uses OpenAI Agents SDK for production-ready reliability
- FileSearchTool provides direct vector store access
- Built-in retry logic and error handling
- Session management for conversation context

## AWS S3 API

- **Purpose:** Scalable file storage for uploaded CSV/XLSX files and generated XML outputs
- **Documentation:** https://docs.aws.amazon.com/s3/latest/API/
- **Base URL(s):** https://s3.amazonaws.com, regional endpoints
- **Authentication:** AWS IAM roles and policies
- **Rate Limits:** 5,500 PUT/COPY/POST/DELETE per prefix per second

**Key Endpoints Used:**
- `PUT /{bucket}/{key}` - File upload for CSV/XLSX and XML files
- `GET /{bucket}/{key}` - File download and retrieval
- `POST /{bucket}?uploads` - Multipart upload for large files

**Integration Notes:**
- Separate buckets for uploads and generated files
- Pre-signed URLs for secure client-side uploads
- CloudFront CDN integration for fast downloads
- Server-side encryption enabled

## Payment Gateway API (Stripe)

- **Purpose:** Secure payment processing for credit purchases and subscription management
- **Documentation:** https://stripe.com/docs/api
- **Base URL(s):** https://api.stripe.com
- **Authentication:** Bearer token (Stripe API key)
- **Rate Limits:** 100 requests per second in live mode

**Key Endpoints Used:**
- `POST /v1/payment_intents` - Create payment for credit purchases
- `POST /v1/customers` - Customer management for subscriptions
- `POST /v1/subscriptions` - Subscription lifecycle management

**Integration Notes:**
- Webhook endpoints for payment status updates
- Strong Customer Authentication (SCA) compliance
- PCI DSS compliance through Stripe
