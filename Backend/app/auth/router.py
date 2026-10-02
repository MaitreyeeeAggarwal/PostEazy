import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = Any

from app.database import get_db
from app.models import UserModel
from app.auth.security import (
    USERS_DB,
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from app.schemas import UserCreate, UserResponse, Token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Any = Depends(get_db)):
    # Check DB if user exists
    existing_user = None
    if db is not None and UserModel is not None:
        try:
            existing_user = db.query(UserModel).filter(
                (UserModel.username == user_in.username) | (UserModel.email == user_in.email)
            ).first()
        except Exception as e:
            print(f"[DB Warning] Could not query user: {e}")

    if existing_user or user_in.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    user_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(user_in.password)

    # Save in DB if available
    if db is not None and UserModel is not None:
        try:
            db_user = UserModel(
                id=user_id,
                username=user_in.username,
                email=user_in.email,
                hashed_password=hashed_pwd
            )
            db.add(db_user)
            db.commit()
        except Exception as e:
            print(f"[DB Warning] Could not save user to DB: {e}")

    # Memory fallback sync
    user_record = {
        "id": user_id,
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": hashed_pwd
    }
    USERS_DB[user_in.username] = user_record

    return UserResponse(id=user_id, username=user_in.username, email=user_in.email)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Any = Depends(get_db)):
    username = form_data.username
    password = form_data.password

    # Try DB lookup first
    user_pwd = None
    db_user = None
    if db is not None and UserModel is not None:
        try:
            db_user = db.query(UserModel).filter(UserModel.username == username).first()
            if db_user:
                user_pwd = db_user.hashed_password
        except Exception as e:
            print(f"[DB Warning] Could not query user on login: {e}")

    if not db_user:
        mem_user = USERS_DB.get(username)
        if mem_user:
            user_pwd = mem_user["hashed_password"]

    if not user_pwd or not verify_password(password, user_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": username})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
