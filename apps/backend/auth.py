from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import User, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple token store (in production use JWT)
_tokens: dict[str, dict] = {}


def _hash_password(password: str) -> str:
    """Hash password with salt using SHA-256 (simple, use bcrypt in production)."""
    salt = os.urandom(32).hex()
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, h = stored.split("$", 1)
        return hmac.compare_digest(hashlib.sha256((salt + password).encode()).hexdigest(), h)
    except (ValueError, AttributeError):
        return False


def create_token(user_id: str) -> str:
    token = str(uuid.uuid4())
    _tokens[token] = {"user_id": user_id, "created_at": time.time()}
    return token


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user from token, returns None if not authenticated."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data = _tokens.get(token)
        if token_data:
            user = db.query(User).filter(User.id == token_data["user_id"]).first()
            return user
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from token, raises 401 if not authenticated."""
    user = get_current_user_optional(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# --- Request/Response Models ---

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_guest: bool


# --- Routes ---

@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        name=req.name or req.email.split("@")[0],
        password_hash=_hash_password(req.password),
        is_guest=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return AuthResponse(
        token=token,
        user={"id": user.id, "email": user.email, "name": user.name, "is_guest": False},
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    token = create_token(user.id)
    return AuthResponse(
        token=token,
        user={"id": user.id, "email": user.email, "name": user.name, "is_guest": user.is_guest},
    )


@router.post("/guest", response_model=AuthResponse)
async def guest_login(db: Session = Depends(get_db)):
    """Create a guest user and return token."""
    guest_id = str(uuid.uuid4())
    user = User(
        id=guest_id,
        email=f"guest-{guest_id[:8]}@local",
        name="游客",
        password_hash="",
        is_guest=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return AuthResponse(
        token=token,
        user={"id": user.id, "email": user.email, "name": "游客", "is_guest": True},
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, name=user.name, is_guest=user.is_guest)


@router.post("/logout")
async def logout(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        _tokens.pop(token, None)
    return {"ok": True}
