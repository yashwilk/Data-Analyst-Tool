from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.auth.security import decode_access_token
from data_analyst_agent.database import repository
from data_analyst_agent.database.database import get_db
from data_analyst_agent.database.model import User

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Missing or invalid authentication token",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED

    email = decode_access_token(credentials.credentials)
    if email is None:
        raise _UNAUTHORIZED

    user = await repository.get_user_by_email(db, email)
    if user is None:
        raise _UNAUTHORIZED

    return user
