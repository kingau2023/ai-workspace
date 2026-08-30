# AI Workspace

AI Workspace is a secure, full-stack knowledge workspace designed for managing user-owned workspaces, notes, uploaded documents, and AI-powered answers grounded in workspace content. The project combines a FastAPI backend, a PostgreSQL database, a Next.js frontend, and Docker-based local deployment into a practical portfolio-ready application for knowledge management and retrieval.

## Repository description suggestion

A full-stack AI workspace for secure knowledge management, featuring JWT-authenticated workspaces, notes, document uploads, and AI-assisted answers grounded in user-owned content using a lightweight retrieval workflow.

## Recommended GitHub topics

- `fastapi`
- `nextjs`
- `postgresql`
- `sqlalchemy`
- `jwt`
- `authentication`
- `rag`
- `ai`
- `knowledge-base`
- `full-stack`
- `docker`
- `alembic`
- `python`
- `typescript`

## Project overview

AI Workspace gives each user a private area to:

- create and manage workspaces
- add and edit notes within a workspace
- upload documents and store text content for retrieval
- ask AI questions that are grounded in the workspace’s content
- keep data isolated by owner and workspace

This project is deliberately structured as a polished, production-minded sample app that shows secure API design, database modeling, frontend dashboard workflows, and deployment-ready configuration.

## Features

- JWT-based user registration and login
- Per-user workspace ownership enforcement
- Workspace, note, and document CRUD operations
- Secure document uploads with size and file type validation
- Text extraction and retrieval over uploaded content and notes
- Lightweight cosine-similarity ranking for AI-style answer grounding
- PostgreSQL persistence with Alembic migrations
- Docker Compose setup for local stack orchestration
- Frontend and backend validation via linting, testing, and production build checks

## Architecture

The application follows a simple layered architecture:

- Backend: FastAPI application with SQLAlchemy models, JWT authentication, ownership checks, upload handling, and workspace-aware retrieval logic
- Database: PostgreSQL for relational data storage and migration-based schema evolution
- Frontend: Next.js application for auth, workspace management, documents, notes, and chat interactions
- DevOps: Docker Compose for local orchestration and GitHub Actions for CI validation

## Tech stack

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- python-jose / bcrypt
- python-multipart
- pytest

### Frontend
- Next.js 16
- React 19
- TypeScript
- Vitest
- Testing Library
- ESLint

### Infrastructure
- Docker
- Docker Compose
- GitHub Actions

## Screenshots

> Add portfolio screenshots here for the sign-in flow, dashboard, workspace detail, notes view, document upload, and AI chat experience.

Example placement:

- Login and registration screen
- Workspace dashboard
- Note editing screen
- Document upload interface
- AI answer panel grounded in workspace content

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm
- Docker and Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/kingau2023/ai-workspace.git
cd ai-workspace
```

### 2. Configure environment files

Copy the example files into local runtime files:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Update values as needed before running the app, especially the JWT secret used by the backend.

### 3. Start the database

```bash
docker compose up -d postgres
```

### 4. Run the backend locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

### 5. Run the frontend locally

```bash
cd frontend
npm install
npm run dev
```

Open the app in a browser at:

- http://localhost:3000

## Docker setup

This repository includes a Docker Compose setup for the full application stack.

From the project root, start the full stack:

```bash
docker compose up --build
```

### Services

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Worker service: containerized background worker defined in the `worker/` directory

### Compose configuration

The project root `docker-compose.yml` defines:

- `postgres`
- `backend`
- `frontend`
- `worker`

The backend service uses `./backend/.env` and the Compose file reads shared environment values from the root `.env` file when available.

## API overview

The backend exposes the core REST endpoints documented in [docs/api.md](docs/api.md).

### Authentication
- `POST /auth/register`
- `POST /auth/login`
- `GET /users/me`

### Workspaces
- `GET /workspaces`
- `POST /workspaces`
- `GET /workspaces/{workspace_id}`
- `PUT /workspaces/{workspace_id}`
- `DELETE /workspaces/{workspace_id}`

### Notes
- `GET /workspaces/{workspace_id}/notes`
- `POST /workspaces/{workspace_id}/notes`
- `GET /workspaces/{workspace_id}/notes/{note_id}`
- `PUT /workspaces/{workspace_id}/notes/{note_id}`
- `DELETE /workspaces/{workspace_id}/notes/{note_id}`

### Documents
- `GET /workspaces/{workspace_id}/documents`
- `POST /workspaces/{workspace_id}/documents`
- `GET /workspaces/{workspace_id}/documents/{document_id}`
- `DELETE /workspaces/{workspace_id}/documents/{document_id}`

### AI chat
- `POST /workspaces/{workspace_id}/ai/chat`

The chat endpoint scores note and document content using a lightweight cosine-similarity retrieval approach and returns the most relevant context for the user’s question.

## Testing instructions

### Backend tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

### Frontend tests and build checks

```bash
cd frontend
npm install
npm run lint
npm run test
npm run build
```

### Docker validation

```bash
docker compose config
```

## Environment variables

The repository includes example files that define the expected configuration.

### Root `.env.example`

```env
POSTGRES_DB=ai_workspace
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/ai_workspace
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=AI Workspace
```

### Backend `.env.example`

```env
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_workspace
UPLOAD_ROOT=/workspaces/ai-workspace/backend/uploads
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ENVIRONMENT=development
```

Notes:

- `JWT_SECRET_KEY` must be changed before any non-local deployment.
- `ALLOWED_ORIGINS` controls permitted frontend origins for CORS.
- `UPLOAD_ROOT` defines where uploaded files are stored on disk.

## Security notes

- Store secrets in local environment files and never commit production credentials.
- Rotate the JWT secret for any environment beyond local development.
- Keep `ALLOWED_ORIGINS` limited to trusted frontend URLs.
- Uploaded files are validated for size and accepted extension/type combinations.
- Workspace, note, and document access are owner-scoped to prevent cross-user access.
- The repository intentionally ignores environment and generated file artifacts through `.gitignore`.

## Project structure

```text
ai-workspace/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── docs/
│   └── api.md
├── backend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── alembic/
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── requirements.txt
│   ├── tests/
│   └── uploads/
├── frontend/
│   ├── Dockerfile
│   ├── eslint.config.mjs
│   ├── next.config.ts
│   ├── package.json
│   ├── public/
│   ├── src/
│   └── vitest.config.ts
├── worker/
│   └── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml
└── .dockerignore
```

## Production notes

This project is ready for Docker-based local development and deployment workflows. For production use, replace example secrets, configure trusted CORS origins, and ensure the database and uploads storage are backed by a managed or persistent environment.

## License

This project is provided as a portfolio and learning project. Review the repository policies before using it for production deployment or commercial distribution.
