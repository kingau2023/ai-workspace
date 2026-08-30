# AI Workspace API overview

The FastAPI backend exposes authenticated workspace, notes, document, and RAG chat endpoints.

## Authentication

- POST /auth/register
- POST /auth/login
- GET /users/me

## Workspaces

- GET /workspaces
- POST /workspaces
- GET /workspaces/{workspace_id}
- PUT /workspaces/{workspace_id}
- DELETE /workspaces/{workspace_id}

## Notes

- GET /workspaces/{workspace_id}/notes
- POST /workspaces/{workspace_id}/notes
- GET /workspaces/{workspace_id}/notes/{note_id}
- PUT /workspaces/{workspace_id}/notes/{note_id}
- DELETE /workspaces/{workspace_id}/notes/{note_id}

## Documents

- GET /workspaces/{workspace_id}/documents
- POST /workspaces/{workspace_id}/documents
- GET /workspaces/{workspace_id}/documents/{document_id}
- DELETE /workspaces/{workspace_id}/documents/{document_id}

## AI chat

- POST /workspaces/{workspace_id}/ai/chat

The chat endpoint scores note and document content using a lightweight cosine-similarity vector search over workspace text and returns the most relevant excerpts with source names.

## Runtime docs

Swagger UI: http://localhost:8000/docs
Redoc: http://localhost:8000/redoc
