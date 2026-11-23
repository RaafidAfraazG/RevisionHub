"""JWT authentication; roles are always read from the database, not token claims."""

import os
import secrets
from datetime import timedelta
from pathlib import Path

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, utc_now


def load_secret() -> str:
    configured = os.getenv("SECRET_KEY")
    if configured:
        return configured
    # Zero-setup development uses a private, persistent random signing key.
    # Deployments should set SECRET_KEY, shared across all API instances.
    path = Path(__file__).resolve().parents[1] / ".jwt-secret"
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_urlsafe(48))
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8").strip()


SECRET_KEY = load_secret()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    now = utc_now()
    return jwt.encode({"sub": str(user.id), "iat": now, "exp": now + timedelta(hours=2),
                       "iss": "revisionhub"}, SECRET_KEY, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(401, "Please log in with a valid, unexpired token.", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"],
                             issuer="revisionhub", options={"require": ["exp", "sub", "iat"]})
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
