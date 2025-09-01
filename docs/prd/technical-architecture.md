# Technical Architecture

  Frontend:
  - Next.js for responsive SPA
  - TypeScript for type safety
  - Tailwind CSS for rapid UI development

  Backend:
  - Python/FastAPI
  - xsdata for parsing XSD schemas 
  - Pydantic for data validation
  - PostgreSQL for data persistence
  - Redis for caching and queues

  AI/ML Layer:
  - Openai-agents SDK (https://github.com/openai/openai-agents-python) for initial matching
  - FileSearch tool for HS code search
  - Openai Vector Store for HS Codes and AI searching

  Infrastructure:
  - AWS/Azure for hosting
  - S3 for file storage
  - CloudFront CDN
  - Docker containerization
