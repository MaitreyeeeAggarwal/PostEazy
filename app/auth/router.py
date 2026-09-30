import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

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
async def register(user_in: UserCreate):
    if user_in.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    user_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(user_in.password)
    user_record = {
        "id": user_id,
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": hashed_pwd
    }
    USERS_DB[user_in.username] = user_record
    return UserResponse(id=user_id, username=user_in.username, email=user_in.email)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
