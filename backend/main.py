from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from auth import UserCreate, UserLogin, UserPublic, create_access_token, get_current_user, get_password_hash, verify_password
from database import SessionLocal, check_db_connection, get_db
from models import User

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
