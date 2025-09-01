# XM-Port

AI-powered customs documentation platform for efficient import/export processing.

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Redis 7.2+

### Environment Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure required variables in `.env`:**
   - `SECRET_KEY`: Generate a secure 32+ character secret key
   - `DATABASE_URL`: PostgreSQL connection string
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `NEXTAUTH_SECRET`: Generate a secure secret for NextAuth

3. **Install dependencies:**
   ```bash
   npm install
   ```

4. **Start development servers:**
   ```bash
   npm run dev
   ```

This will start:
- Frontend: http://localhost:3000 (Next.js)
- Backend: http://localhost:8000 (FastAPI)
- API Documentation: http://localhost:8000/api/docs

## Project Structure

```
xm-port/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── shared/       # Shared TypeScript types
│   ├── ui/           # Shared UI components
│   └── config/       # Shared configurations
└── infrastructure/   # AWS CDK for deployment
```

## Development

- **Frontend**: Next.js 15 with TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI with Python 3.11+, PostgreSQL, Redis
- **Shared Types**: TypeScript definitions in `packages/shared`

## Available Scripts

- `npm run dev` - Start development servers
- `npm run build` - Build all applications
- `npm run test` - Run all tests
- `npm run lint` - Lint all code
- `npm run format` - Format code with Prettier

## Environment Variables

See `.env.example` for all required environment variables.

### Required Variables

- `SECRET_KEY` - Backend security secret (32+ characters)
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key for AI processing
- `NEXTAUTH_SECRET` - NextAuth.js security secret

### Optional Variables

- `REDIS_URL` - Redis connection (defaults to localhost)
- `AWS_*` - AWS configuration for production file storage
- `SENTRY_DSN` - Error tracking (recommended for production)

## License

MIT