"""
Authentication module for Home Health Analytics API.

Provides JWT-based authentication with hardcoded credentials for development.
In production, set environment variables AUTH_USERNAME, AUTH_PASSWORD, and SECRET_KEY.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ============================================
# Configuration
# ============================================

# IMPORTANT: In production, these MUST be set via environment variables
# The defaults below are ONLY for development/testing
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-abc123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours default

# Hardcoded credentials for development
# In production, set AUTH_USERNAME and AUTH_PASSWORD environment variables
DEV_USERNAME = "admin"
DEV_PASSWORD = "VPs@Zk9*@ymG"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


# ============================================
# Models
# ============================================

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class User(BaseModel):
    username: str


# ============================================
# User Store (Hardcoded for development)
# ============================================

def get_users_db() -> dict:
    """
    Get the users database.
    In development: uses hardcoded credentials.
    In production: uses environment variables.
    """
    username = os.getenv("AUTH_USERNAME", DEV_USERNAME)
    password = os.getenv("AUTH_PASSWORD", DEV_PASSWORD)

    # Hash the password (in a real app, passwords would be pre-hashed)
    hashed_password = pwd_context.hash(password)

    return {
        username: {
            "username": username,
            "hashed_password": hashed_password
        }
    }


# ============================================
# Password Utilities
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


# ============================================
# User Authentication
# ============================================

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by username and password.
    Returns the user dict if successful, None otherwise.
    """
    # Get configured credentials
    expected_username = os.getenv("AUTH_USERNAME", DEV_USERNAME)
    expected_password = os.getenv("AUTH_PASSWORD", DEV_PASSWORD)

    # Check credentials directly (simpler for single-user system)
    if username == expected_username and password == expected_password:
        return {"username": username}

    return None


# ============================================
# JWT Token Handling
# ============================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify a JWT token and return the token data."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            return None

        return TokenData(username=username)
    except JWTError:
        return None


# ============================================
# FastAPI Dependencies
# ============================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    Raises HTTPException if authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data = verify_token(token)

    if token_data is None or token_data.username is None:
        raise credentials_exception

    return User(username=token_data.username)


# ============================================
# Login Function
# ============================================

def login(username: str, password: str) -> Optional[Token]:
    """
    Attempt to log in a user.
    Returns a Token if successful, None otherwise.
    """
    user = authenticate_user(username, password)

    if not user:
        return None

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )
