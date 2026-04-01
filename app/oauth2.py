from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.schemas import TokenPayload

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hash_password(password: str) -> str:
    # Password hashing is CPU-bound and should not block the event loop.
    import asyncio

    return await asyncio.to_thread(pwd_context.hash, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    import asyncio

    return await asyncio.to_thread(pwd_context.verify, plain_password, hashed_password)


async def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    import asyncio

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expire, "typ": token_type}
    return await asyncio.to_thread(jwt.encode, to_encode, settings.secret_key, settings.algorithm)


async def create_access_token(subject: str) -> str:
    return await create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


async def create_refresh_token(subject: str) -> str:
    return await create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


async def decode_token(token: str) -> TokenPayload:
    import asyncio

    try:
        payload = await asyncio.to_thread(
            jwt.decode,
            token,
            settings.secret_key,
            [settings.algorithm],
        )
        return TokenPayload(**payload)
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
