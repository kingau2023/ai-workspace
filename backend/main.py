from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from auth import UserCreate, UserLogin, UserPublic, create_access_token, get_current_user, get_password_hash, verify_password
from database import check_db_connection, get_db
from models import Note, User, Workspace


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteCreate(BaseModel):
    title: str
    content: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class NoteRead(BaseModel):
    id: int
    title: str
    content: str | None = None
    workspace_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


app = FastAPI(
    title="AI Workspace API",
    version="0.1.0",
)


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
