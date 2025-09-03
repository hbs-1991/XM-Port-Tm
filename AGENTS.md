# Repository Guidelines

## Project Structure & Module Organization
- apps/web: Next.js frontend (TypeScript, Tailwind, Playwright/Jest).
- apps/api: FastAPI backend (Python 3.11, SQLAlchemy, Alembic, Pytest).
- packages/shared: Shared TypeScript types and utilities.
- packages/ui: Shared UI components.
- packages/config: Centralized ESLint/TS/Tailwind configs.
- infrastructure: Deployment scripts and IaC.
- docs, scripts: Documentation and helper scripts.

## Build, Test, and Development Commands
- npm run dev: Start web and API in watch mode.
- npm run dev:web | dev:api: Start a single app.
- npm run build: Build shared first, then all workspaces.
- npm run test | test:watch: Run workspace tests (Jest, Pytest via workspaces).
- npm run test:e2e: Run Playwright E2E tests for web.
- npm run lint | lint:fix: Lint all packages (ESLint/Prettier/Black).
- npm run format: Format repo with Prettier.
- npm run db:migrate: Apply Alembic migrations (API).
- npm run db:seed: Seed demo data (requires backend running/local DB).
- scripts/dev.sh: Docker-backed dev startup for Postgres/Redis.

## Coding Style & Naming Conventions
- TypeScript: 2‑space indent; Prettier enforced (.prettierrc). Components PascalCase; variables camelCase; test files *.test.ts(x)/*.spec.ts(x).
- Python: Black (line-length 88) and isort via lint-staged; modules snake_case; tests test_*.py.
- Linting: ESLint configs in packages/config; fix before pushing (use npm run lint:fix).

## Testing Guidelines
- Web unit/integration: Jest (apps/web/tests, *.test.tsx). E2E: Playwright (npm run test:e2e).
- API tests: Pytest in apps/api/tests (run via root npm test or cd apps/api && pytest).
- Aim to cover critical paths (auth, file upload, XML generation). Add fixtures over mocks where possible.

## Commit & Pull Request Guidelines
- Commits: History favors descriptive messages (often multi-sentence). Use a concise summary line, then details and rationale. Example: "Fix XML root validation: enforce required tags; add tests." Link issue IDs when available.
- PRs: Clear description, scope, and checklist; link related issues; include screenshots for UI changes; note migration steps (db:migrate) and env keys if added; ensure linters/tests pass.

## Security & Configuration
- Never commit secrets. Copy .env.example → .env and set DATABASE_URL, SECRET_KEY, NEXTAUTH_SECRET, OPENAI_API_KEY, etc.
- Use Docker compose (scripts/dev.sh) for local Postgres/Redis parity.
