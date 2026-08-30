import os
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
import re

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import UserCreate, UserLogin, UserPublic, create_access_token, get_current_user, get_password_hash, verify_password
from database import check_db_connection, get_db
from models import Document, Note, User, Workspace

UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "/workspaces/ai-workspace/backend/uploads"))
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "10485760"))
ALLOWED_UPLOAD_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".pdf"}
ALLOWED_UPLOAD_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
    "application/octet-stream",
}


def sanitize_filename(filename: str) -> str:
    candidate = PurePosixPath(filename).name
    candidate = candidate.strip() or "uploaded-file"
    stem, suffix = os.path.splitext(candidate)
    safe_stem = re.sub(r"[^A-Za-z0-9._-]", "-", stem)[:120] or "uploaded-file"
    safe_suffix = suffix.lower() if suffix.lower() in ALLOWED_UPLOAD_EXTENSIONS else ""
    unique_suffix = uuid.uuid4().hex[:8]
    safe_name = f"{safe_stem}-{unique_suffix}{safe_suffix}" if safe_suffix else f"{safe_stem}-{unique_suffix}"
    return safe_name[:255] or "uploaded-file"


def validate_upload_file(filename: str, content_type: str | None, size_bytes: int) -> None:
    if size_bytes <= 0 or size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File size exceeds {MAX_UPLOAD_BYTES} bytes")

    extension = os.path.splitext(filename.lower())[1]
    if content_type and content_type not in ALLOWED_UPLOAD_CONTENT_TYPES and content_type.startswith("text/") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
    if extension and extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file extension")
    if not extension and not content_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class WorkspaceRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    content: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    content: str | None = None


class NoteRead(BaseModel):
    id: int
    title: str
    content: str | None = None
    workspace_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    id: int
    title: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    text_content: str | None = None
    workspace_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=12)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    score: float


app = FastAPI(
    title="AI Workspace API",
    version="1.0.0",
    description="Authentication, workspace management, document uploads, and AI-powered notebook search for the AI Workspace project.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_vector(text: str | None) -> Counter[str]:
    if not text:
        return Counter()
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return Counter(tokens)


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    left_values = left.values()
    right_values = right.values()
    numerator = sum(left[token] * right[token] for token in set(left) & set(right))
    left_norm = sum(value * value for value in left_values) ** 0.5
    right_norm = sum(value * value for value in right_values) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def get_own_workspace(db: Session, current_user: User, workspace_id: int) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.owner_id == current_user.id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def get_own_note(db: Session, current_user: User, workspace_id: int, note_id: int) -> Note:
    note = (
        db.query(Note)
        .join(Workspace)
        .filter(Note.id == note_id, Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def get_own_document(db: Session, current_user: User, workspace_id: int, document_id: int) -> Document:
    document = (
        db.query(Document)
        .join(Workspace)
        .filter(Document.id == document_id, Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db/health")
def db_health_check():
    result = check_db_connection()
    return {"status": "ok", "database": "connected", "result": result}


@app.post("/auth/register")
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.email == payload.email) | (User.username == payload.username)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer", "user": UserPublic.model_validate(user)}


@app.post("/auth/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer", "user": UserPublic.model_validate(user)}


@app.get("/users/me", response_model=UserPublic)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/workspaces", response_model=list[WorkspaceRead])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Workspace).filter(Workspace.owner_id == current_user.id).order_by(Workspace.created_at.desc()).all()


@app.post("/workspaces", response_model=WorkspaceRead)
def create_workspace(payload: WorkspaceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = Workspace(name=payload.name, description=payload.description, owner_id=current_user.id)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@app.get("/workspaces/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_own_workspace(db, current_user, workspace_id)


@app.put("/workspaces/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = get_own_workspace(db, current_user, workspace_id)
    if payload.name is not None:
        workspace.name = payload.name
    if payload.description is not None:
        workspace.description = payload.description
    db.commit()
    db.refresh(workspace)
    return workspace


@app.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = get_own_workspace(db, current_user, workspace_id)
    db.delete(workspace)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/workspaces/{workspace_id}/notes", response_model=list[NoteRead])
def list_notes_for_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_own_workspace(db, current_user, workspace_id)
    return (
        db.query(Note)
        .join(Workspace)
        .filter(Note.workspace_id == workspace_id, Workspace.owner_id == current_user.id)
        .order_by(Note.created_at.desc())
        .all()
    )


@app.post("/workspaces/{workspace_id}/notes", response_model=NoteRead)
def create_note_for_workspace(
    workspace_id: int,
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = get_own_workspace(db, current_user, workspace_id)
    note = Note(title=payload.title, content=payload.content, workspace_id=workspace.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.get("/workspaces/{workspace_id}/notes/{note_id}", response_model=NoteRead)
def get_note_for_workspace(
    workspace_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_own_note(db, current_user, workspace_id, note_id)


@app.put("/workspaces/{workspace_id}/notes/{note_id}", response_model=NoteRead)
def update_note_for_workspace(
    workspace_id: int,
    note_id: int,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = get_own_note(db, current_user, workspace_id, note_id)
    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    db.commit()
    db.refresh(note)
    return note


@app.delete("/workspaces/{workspace_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_for_workspace(
    workspace_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = get_own_note(db, current_user, workspace_id, note_id)
    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/workspaces/{workspace_id}/documents", response_model=list[DocumentRead])
def list_documents_for_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_own_workspace(db, current_user, workspace_id)
    return (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id, Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@app.post("/workspaces/{workspace_id}/documents", response_model=DocumentRead)
async def upload_document_for_workspace(
    workspace_id: int,
    title: str = Form(default=""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = get_own_workspace(db, current_user, workspace_id)
    file_bytes = await file.read()
    original_name = file.filename or "uploaded-file"
    validate_upload_file(original_name, file.content_type, len(file_bytes))
    filename = sanitize_filename(original_name)
    safe_title = title.strip() or Path(filename).stem
    storage_dir = UPLOAD_ROOT / str(current_user.id) / str(workspace.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / filename
    storage_path.write_bytes(file_bytes)

    text_content = ""
    if file.content_type and "text" in file.content_type:
        text_content = file_bytes.decode("utf-8", errors="ignore")
    elif file.filename and file.filename.lower().endswith((".md", ".txt", ".csv", ".json")):
        text_content = file_bytes.decode("utf-8", errors="ignore")

    document = Document(
        title=safe_title,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(file_bytes),
        storage_path=str(storage_path),
        text_content=text_content,
        workspace_id=workspace.id,
        owner_id=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@app.get("/workspaces/{workspace_id}/documents/{document_id}", response_model=DocumentRead)
def get_document_for_workspace(
    workspace_id: int,
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_own_document(db, current_user, workspace_id, document_id)


@app.delete("/workspaces/{workspace_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_for_workspace(
    workspace_id: int,
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = get_own_document(db, current_user, workspace_id, document_id)
    storage_path = Path(document.storage_path)
    if storage_path.exists():
        storage_path.unlink()
    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/workspaces/{workspace_id}/ai/chat", response_model=ChatResponse)
def chat_with_workspace(
    workspace_id: int,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = get_own_workspace(db, current_user, workspace_id)
    notes = db.query(Note).filter(Note.workspace_id == workspace.id).all()
    documents = db.query(Document).filter(Document.workspace_id == workspace.id, Document.owner_id == current_user.id).all()

    question_vector = build_vector(payload.message)
    candidates: list[tuple[float, str, str]] = []

    for note in notes:
        context = f"{note.title} {note.content or ''}"
        score = cosine_similarity(question_vector, build_vector(context))
        candidates.append((score, note.title, context))

    for document in documents:
        context = f"{document.title} {document.text_content or ''}"
        score = cosine_similarity(question_vector, build_vector(context))
        candidates.append((score, document.title, context))

    if not candidates:
        answer = "I do not see workspace content yet. Add notes or upload documents to enable grounded answers."
        return ChatResponse(answer=answer, sources=[], score=0.0)

    ranked = sorted(candidates, key=lambda item: item[0], reverse=True)[: payload.limit]
    sources = [source for _, source, _ in ranked if source]
    best_score = ranked[0][0]
    relevant_context = "\n\n".join(context for _, _, context in ranked if context)
    answer = (
        "Based on your workspace context: "
        + relevant_context[:700].strip()
        + "\n\n"
        + f"The most relevant material for '{payload.message}' is in {', '.join(sources[:3]) if sources else 'your workspace'} ."
    )

    return ChatResponse(answer=answer, sources=sources, score=float(best_score))
