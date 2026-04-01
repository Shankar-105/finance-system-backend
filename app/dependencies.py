from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_redis
from app.config import get_settings
from app.models import TokenBlacklist, User, UserRole
from app.oauth2 import decode_token
from app.schemas import TokenPayload
from app.services.rate_limiter import fixed_window_rate_limiter


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
settings = get_settings()


async def _is_blacklisted(redis: Redis, jti: str) -> bool:
    try:
        return bool(await redis.get(f"blacklist:{jti}"))
    except RedisError:
        return False


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: TokenPayload = await decode_token(token)
    except ValueError as exc:
        raise credentials_exception from exc

    if payload.typ != "access":
        raise credentials_exception

    if await _is_blacklisted(redis, payload.jti):
        raise credentials_exception

    blacklisted = await db.scalar(select(TokenBlacklist).where(TokenBlacklist.jti == payload.jti))
    if blacklisted is not None:
        raise credentials_exception

    try:
        user_id = int(payload.sub)
    except ValueError as exc:
        raise credentials_exception from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    async def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_dependency


sensitive_route_limiter = fixed_window_rate_limiter(
    key_prefix="sensitive",
    max_requests=settings.sensitive_rate_limit_max_requests,
    window_seconds=settings.sensitive_rate_limit_window_seconds,
)
