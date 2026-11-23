from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])
# Equalize password-check work for unknown users without exposing account existence.
_DUMMY_HASH = hash_password("not-a-real-account-password")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    valid = verify_password(payload.password, user.hashed_password if user else _DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(401, "Invalid username or password.", headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
