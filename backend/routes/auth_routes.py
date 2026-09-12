from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = ""

class UserLoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    # Check username uniqueness
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered"
        )
    # Check email uniqueness
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    hashed_pw = hash_password(req.password)
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hashed_pw,
        full_name=req.full_name or req.username,
        avatar_url="/static/images/default_avatar.svg"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@router.post("/login")
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token({"sub": user.username, "user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@router.get("/me")
def get_authenticated_user_profile(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()
