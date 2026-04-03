import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db, get_redis
from app.dependencies import (
    get_current_user,
    oauth2_scheme,
    require_roles,
    sensitive_route_limiter,
)
from app.models import User, UserRole
from app.oauth2 import hash_password
from app.schemas import (
    AdminUserCreate,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
)
from app.services.auth_service import (
    authenticate_user,
    issue_token_pair,
    refresh_access_pair,
    revoke_token_if_present,
)
from app.services.presence_service import get_online_user_ids

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/bootstrap-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def bootstrap_admin(
    payload: UserCreate,
    bootstrap_key: str | None = Header(default=None, alias="X-Bootstrap-Key"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(sensitive_route_limiter),
) -> UserOut:
    settings = get_settings()
    if not settings.admin_bootstrap_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin bootstrap is disabled",
        )

    if bootstrap_key is None or not hmac.compare_digest(bootstrap_key, settings.admin_bootstrap_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap key",
        )

    existing_admin = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    if existing_admin is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap can only be used before first admin exists",
        )

    existing_user = await db.scalar(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with provided email or username already exists",
        )

    hashed_password = await hash_password(payload.password)
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(sensitive_route_limiter),
) -> UserOut:
    if payload.role != UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is limited to viewer role",
        )

    existing = await db.scalar(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with provided email or username already exists",
        )

    hashed_password = await hash_password(payload.password)
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed_password,
        role=UserRole.VIEWER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login", response_model=Token)
async def login_user(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(sensitive_route_limiter),
) -> Token:
    user = await authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return await issue_token_pair(db, user.id)


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _: None = Depends(sensitive_route_limiter),
) -> Token:
    try:
        return await refresh_access_pair(db, redis, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(oauth2_scheme),
    _: None = Depends(sensitive_route_limiter),
) -> MessageResponse:
    _ = current_user
    await revoke_token_if_present(db, redis, access_token)
    if payload.refresh_token:
        await revoke_token_if_present(db, redis, payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("/admin/ping", response_model=MessageResponse)
async def admin_ping(
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    return MessageResponse(message="Admin access granted")


@router.get("/admin/online-users", response_model=list[int])
async def get_online_users(
    redis: Redis = Depends(get_redis),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[int]:
    return await get_online_user_ids(redis)


@router.post("/admin/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    __: None = Depends(sensitive_route_limiter),
) -> UserOut:
    if payload.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use role update flow for admin promotion",
        )

    existing = await db.scalar(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with provided email or username already exists",
        )

    hashed_password = await hash_password(payload.password)
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed_password,
        role=UserRole(payload.role.value),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/admin/users/{user_id}", response_model=UserOut)
async def update_user_by_admin(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    __: None = Depends(sensitive_route_limiter),
) -> UserOut:
    if payload.role is None and payload.is_active is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.role is not None:
        user.role = UserRole(payload.role.value)

    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)
