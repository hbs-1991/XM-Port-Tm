# Unified Project Structure

```
xm-port/
├── .github/                    # CI/CD workflows
│   └── workflows/
│       ├── ci.yaml
│       └── deploy.yaml
├── apps/                       # Application packages
│   ├── web/                    # Frontend application (Next.js)
│   │   ├── src/
│   │   │   ├── app/            # App Router structure
│   │   │   │   ├── (public)/   # Landing pages
│   │   │   │   ├── (dashboard)/# User dashboard
│   │   │   │   ├── (admin)/    # Admin panel
│   │   │   │   └── api/        # API routes
│   │   │   ├── components/     # React components
│   │   │   │   ├── landing/    # Landing page components
│   │   │   │   ├── dashboard/  # Dashboard components
│   │   │   │   ├── admin/      # Admin components
│   │   │   │   └── shared/     # Shared UI components
│   │   │   ├── lib/            # Frontend utilities
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── stores/         # Zustand stores
│   │   │   ├── services/       # API client services
│   │   │   └── styles/         # Global styles
│   │   ├── public/             # Static assets
│   │   ├── tests/              # Frontend tests
│   │   └── package.json
│   └── api/                    # Backend application (FastAPI)
│       ├── src/
│       │   ├── main.py         # FastAPI application entry
│       │   ├── api/            # API routes
│       │   │   ├── v1/         # API version 1
│       │   │   │   ├── auth.py # Authentication endpoints
│       │   │   │   ├── processing.py # File processing
│       │   │   │   ├── admin.py # Admin endpoints
│       │   │   │   └── ws.py   # WebSocket handlers
│       │   ├── services/       # Business logic
│       │   │   ├── auth_service.py
│       │   │   ├── file_processing.py
│       │   │   ├── ai_matching.py
│       │   │   ├── xml_generation.py
│       │   │   └── analytics.py
│       │   ├── models/         # Database models
│       │   │   ├── user.py
│       │   │   ├── processing_job.py
│       │   │   └── hs_code.py
│       │   ├── repositories/   # Data access layer
│       │   ├── schemas/        # Pydantic schemas
│       │   ├── core/           # Core configuration
│       │   └── utils/          # Backend utilities
│       ├── tests/              # Backend tests
│       ├── alembic/            # Database migrations
│       └── requirements.txt
├── packages/                   # Shared packages
│   ├── shared/                 # Shared types/utilities
│   │   ├── src/
│   │   │   ├── types/          # TypeScript interfaces
│   │   │   │   ├── user.ts
│   │   │   │   ├── processing.ts
│   │   │   │   └── admin.ts
│   │   │   ├── constants/      # Shared constants
│   │   │   ├── utils/          # Shared utilities
│   │   │   └── schemas/        # Validation schemas
│   │   └── package.json
│   ├── ui/                     # Shared UI components (shadcn/ui)
│   │   ├── src/
│   │   │   ├── components/     # Base UI components
│   │   │   └── styles/         # Component styles
│   │   └── package.json
│   └── config/                 # Shared configuration
│       ├── eslint/
│       ├── typescript/
│       ├── tailwind/
│       └── jest/
├── infrastructure/             # Infrastructure as Code
│   ├── aws-cdk/               # AWS CDK definitions
│   │   ├── lib/
│   │   │   ├── database-stack.ts
│   │   │   ├── storage-stack.ts
│   │   │   ├── compute-stack.ts
│   │   │   └── monitoring-stack.ts
│   │   └── bin/
├── scripts/                    # Build/deploy scripts
│   ├── build.sh
│   ├── deploy.sh
│   ├── db-migrate.sh
│   └── seed-data.sh
├── docs/                       # Documentation
│   ├── prd.md
│   ├── architecture.md         # This document
│   ├── api-reference.md
│   ├── deployment.md
│   └── user-guide.md
├── .env.example                # Environment template
├── package.json                # Root package.json (workspace config)
├── docker-compose.yml          # Local development environment
├── Dockerfile.web              # Frontend container
├── Dockerfile.api              # Backend container
└── README.md
```
