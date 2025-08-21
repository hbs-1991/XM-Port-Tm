# Tech Stack

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| Frontend Language | TypeScript | 5.3+ | Type-safe development across entire stack | Eliminates runtime type errors, excellent IDE support, shared types between frontend/backend |
| Frontend Framework | Next.js | 15.1+ | Full-stack React framework with App Router | Handles landing page (SSG), dashboard (SSR), and admin panel with unified codebase |
| UI Component Library | shadcn/ui + Headless UI | Latest | Accessible, customizable component library | Perfect integration with Tailwind, accessibility-first, highly customizable |
| State Management | Zustand + React Query | Zustand 4.4+, RQ 5.0+ | Client state + server state management | Lightweight state management with excellent async data handling |
| Backend Language | Python | 3.11+ | AI/ML ecosystem compatibility | Best ecosystem for AI integrations, excellent async support |
| Backend Framework | FastAPI | 0.108+ | High-performance async Python web framework | Automatic OpenAPI docs, excellent async support, perfect for AI workloads |
| API Style | REST + WebSocket | HTTP/1.1 + WS | RESTful APIs with real-time capabilities | Simple, well-understood pattern with real-time file processing updates |
| Database | PostgreSQL | 15+ | Primary data store | ACID compliance, robust relational database for application data |
| Cache | Redis | 7.2+ | Caching and session management | High-performance caching, real-time counters, session storage |
| File Storage | AWS S3 | Latest | Scalable file storage | Industry standard, excellent CDN integration, cost-effective |
| Authentication | NextAuth.js | 4.24+ | Full-stack authentication solution | Seamless Next.js integration, multiple providers, JWT + database sessions |
| Frontend Testing | Jest + React Testing Library | Jest 29+, RTL 14+ | Unit and integration testing | Industry standard React testing with excellent TypeScript support |
| Backend Testing | pytest + httpx | pytest 7+, httpx 0.25+ | API testing and async test support | Excellent FastAPI testing support, async-first testing |
| E2E Testing | Playwright | 1.40+ | Cross-browser end-to-end testing | Modern E2E testing with excellent debugging and CI integration |
| Build Tool | npm | 10+ | Package management and build orchestration | Native Node.js package manager, workspace support |
| Bundler | Turbopack (Next.js 15) | Built-in | Fast development and production builds | Next.js 15 default, 5x faster than Webpack |
| IaC Tool | AWS CDK | 2.100+ | Infrastructure as Code | TypeScript-based infrastructure, excellent AWS integration |
| CI/CD | GitHub Actions | Latest | Automated testing and deployment | Free for public repos, excellent ecosystem, easy to configure |
| Monitoring | DataDog + Sentry | Latest | Application performance and error monitoring | Comprehensive monitoring, excellent FastAPI/Next.js integration |
| Logging | Structured logging (pino + winston) | Latest | Centralized logging with structured data | JSON-based logging for easy parsing and alerting |
| CSS Framework | Tailwind CSS | 3.3+ | Utility-first CSS framework | Rapid development, excellent responsive design, perfect component integration |

**Key Technology Integration Points:**

**AI/ML Stack:**
- **OpenAI Agents SDK** (Latest): Production-ready AI agent orchestration for HS code matching
- **FileSearchTool**: Built-in vector store integration with OpenAI Agents SDK
- **OpenAI Vector Store**: External managed vector storage for HS code embeddings (no local database required)
- **Pydantic** (2.5+): Data validation and settings management
- **xsdata** (23.8+): XSD schema parsing and XML generation

**MCP`s**
- **MCP Context7** : Use before creating AI Agents with openai-agents