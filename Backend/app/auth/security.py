import datetime
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = Any

try:
    from jose import JWTError, jwt
except ImportError:
    import jwt
    JWTError = jwt.PyJWTError

from passlib.context import CryptContext

from app.config import settings
from app.schemas import TokenData, UserResponse
from app.database import get_db
from app.models import UserModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Simple in-memory fallback user database
USERS_DB: Dict[str, dict] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Any = Depends(get_db)
) -> UserResponse:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = None
    if db is not None and UserModel is not None:
        try:
            user = db.query(UserModel).filter(UserModel.username == token_data.username).first()
        except Exception as e:
            print(f"[DB Warning] Could not query user from DB: {e}")

    if user:
        return UserResponse(id=user.id, username=user.username, email=user.email)

    # In-memory fallback check
    mem_user = USERS_DB.get(token_data.username)
    if mem_user is not None:
        return UserResponse(id=mem_user["id"], username=mem_user["username"], email=mem_user["email"])

    raise credentials_exception


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Any = Depends(get_db)
) -> Optional[UserResponse]:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
