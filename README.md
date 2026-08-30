# AI Workspace

AI Workspace is a secure personal knowledge workspace built with FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT auth, and a Next.js frontend. It supports workspaces, notes, document uploads, and a lightweight RAG-style chat powered by workspace content similarity search.

## Architecture

- Backend: FastAPI API with SQLAlchemy models, JWT auth, Alembic migrations, file storage, and workspace AI search endpoints.
- Database: PostgreSQL with persistent Docker volume.
- Frontend: Next.js app for authentication, dashboard, workspace management, notes, documents, and chat.
- Worker: background service for future async workloads and queue processing.

## Features

- User registration and login with JWT authentication
- Workspace CRUD with owner-scoped access
- Notes CRUD inside individual workspaces
- Document upload and storage with ownership enforcement
- RAG-inspired chat using vector-style similarity ranking over notes and uploaded documents
- PostgreSQL schema management via Alembic migrations
- Dockerized local development and deployment-ready configuration
- CI pipeline for backend/frontend verification

## Local development

1. Copy environment files:
   - cp .env.example .env
   - cp backend/.env.example backend/.env
2. Start infrastructure:
   - docker compose up -d postgres
3. Activate backend virtual environment and install dependencies:
   - cd backend
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
   - alembic upgrade head
4. Run backend:
   - uvicorn main:app --reload --host 0.0.0.0 --port 8000
5. Run frontend:
   - cd frontend
   - npm install
   - npm run dev
6. Open http://localhost:3000

## Production-like stack

- Use docker compose up --build
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Database: localhost:5432

## Security notes

- Secrets are stored in local `.env` files and ignored by Git.
- JWT secret must be rotated for production.
- Uploaded document files are stored under backend/uploads and are scoped by user and workspace.
- Owner checks are enforced on workspace, note, and document access.

## CI and quality checks

- Backend: pytest
- Frontend: npm run lint and npm run build
- Docker: docker compose config

## Deployment

This project is ready for container-based deployment via Docker Compose or a managed hosting platform with environment variables configured from `.env.example`.
