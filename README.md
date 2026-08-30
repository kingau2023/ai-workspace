# AI Workspace

AI Workspace is a secure knowledge workspace for managing user-owned workspaces, notes, uploaded documents, and AI-assisted retrieval grounded in workspace content.

## Architecture

- Backend: FastAPI application with SQLAlchemy models, JWT-based auth, ownership checks, upload handling, and a lightweight RAG-style similarity search.
- Database: PostgreSQL managed with Alembic migrations.
- Frontend: Next.js app with authentication, dashboard, workspace management, notes, documents, and chat UI.
- DevOps: Docker Compose for Postgres, backend, frontend, and worker services; GitHub Actions for CI.

## Features

- Secure registration and login with JWT access tokens
- User-scoped workspace CRUD with ownership enforcement
- Notes CRUD under each workspace
- Document upload and storage with per-user/per-workspace file isolation
- AI chat grounded in note and document text using cosine-similarity ranking
- Production-ready environment configuration and CORS hardening
- PostgreSQL migration workflow via Alembic
- CI verification for backend tests, frontend lint/tests/build, and Docker config validation

## Project structure

- backend/: FastAPI app, auth, database, models, Alembic migrations, tests
- frontend/: Next.js app with UI and tests
- docs/: API reference and supporting documentation
- docker-compose.yml: local multi-service stack
- .github/workflows/ci.yml: CI pipeline

## Environment setup

1. Copy the example environment files:
   - cp .env.example .env
   - cp backend/.env.example backend/.env
2. Update secrets before production use, especially JWT_SECRET_KEY.
3. Start PostgreSQL:
   - docker compose up -d postgres

## Local development

Backend:

- cd backend
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- alembic upgrade head
- uvicorn main:app --reload --host 0.0.0.0 --port 8000

Frontend:

- cd frontend
- npm install
- npm run dev

Open http://localhost:3000

API docs are available at http://localhost:8000/docs.

## Docker workflow

Run the full stack locally:

- docker compose up --build

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

## Security notes

- Secrets are stored in local .env files and ignored by Git.
- JWT secret should be rotated for any non-local deployment.
- Uploaded files are stored inside a per-user, per-workspace path under backend/uploads.
- Ownership checks are enforced on workspaces, notes, and documents.
- CORS origins are configurable through ALLOWED_ORIGINS.

## Quality checks

- Backend: pytest
- Frontend: npm run lint, npm run test, npm run build
- Docker: docker compose config

## Deployment

This project is ready for Docker-based deployments or managed hosting by setting environment variables from the example files and using the included Compose configuration.
