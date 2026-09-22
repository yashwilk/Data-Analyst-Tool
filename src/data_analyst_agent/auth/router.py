from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.auth.schema import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from data_analyst_agent.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from data_analyst_agent.database import repository
from data_analyst_agent.database.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await repository.get_user_by_email(db, body.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = await repository.create_user(db, email=body.email, hashed_password=hash_password(body.password))
    return TokenResponse(access_token=create_access_token(user.email))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await repository.get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return TokenResponse(access_token=create_access_token(user.email))
