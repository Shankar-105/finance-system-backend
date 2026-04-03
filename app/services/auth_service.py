from datetime import datetime, timezone
import logging

from sqlalchemy.dialects.postgresql import insert
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken, TokenBlacklist, User
from app.oauth2 import (
	create_access_token,
	create_refresh_token,
	decode_token,
	exp_to_datetime,
	verify_password,
)
from app.schemas import Token

logger = logging.getLogger(__name__)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
	user = await db.scalar(select(User).where(User.email == email))
	if user is None or not user.is_active:
		return None

	password_valid = await verify_password(password, user.hashed_password)
	if not password_valid:
		return None
	return user


async def _store_refresh_token(db: AsyncSession, user_id: int, refresh_token: str) -> RefreshToken:
	payload = await decode_token(refresh_token)
	refresh_row = RefreshToken(
		jti=payload.jti,
		user_id=user_id,
		expires_at=exp_to_datetime(payload.exp),
	)
	db.add(refresh_row)
	await db.flush()
	return refresh_row


async def issue_token_pair(db: AsyncSession, user_id: int) -> Token:
	subject = str(user_id)
	access_token = await create_access_token(subject)
	refresh_token = await create_refresh_token(subject)
	await _store_refresh_token(db, user_id, refresh_token)
	await db.commit()
	return Token(access_token=access_token, refresh_token=refresh_token)


async def _blacklist_token(
	db: AsyncSession,
	redis: Redis | None,
	jti: str,
	token_type: str,
	expires_at: datetime,
	persist_db: bool = True,
) -> None:
	if persist_db:
		stmt = insert(TokenBlacklist).values(
			jti=jti,
			token_type=token_type,
			expires_at=expires_at,
		)
		stmt = stmt.on_conflict_do_nothing(index_elements=[TokenBlacklist.jti])
		await db.execute(stmt)

	ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
	if ttl_seconds > 0 and redis is not None:
		try:
			await redis.set(f"blacklist:{jti}", "1", ex=ttl_seconds)
		except RedisError as exc:
			logger.warning("Failed to write token blacklist to Redis for jti=%s: %s", jti, exc)


async def refresh_access_pair(db: AsyncSession, redis: Redis, refresh_token: str) -> Token:
	payload = await decode_token(refresh_token)
	if payload.typ != "refresh":
		raise ValueError("Invalid refresh token type")

	try:
		if await redis.get(f"blacklist:{payload.jti}"):
			raise ValueError("Refresh token revoked")
	except RedisError:
		pass

	token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.jti))
	if token_row is None:
		raise ValueError("Refresh token not recognized")
	if token_row.revoked_at is not None:
		raise ValueError("Refresh token already used")
	if token_row.expires_at <= datetime.now(timezone.utc):
		raise ValueError("Refresh token expired")

	user = await db.get(User, int(payload.sub))
	if user is None or not user.is_active:
		raise ValueError("User is inactive")

	token_row.revoked_at = datetime.now(timezone.utc)

	new_access_token = await create_access_token(str(user.id))
	new_refresh_token = await create_refresh_token(str(user.id))

	new_refresh_payload = await decode_token(new_refresh_token)
	token_row.replaced_by_jti = new_refresh_payload.jti

	await _blacklist_token(
		db=db,
		redis=None,
		jti=payload.jti,
		token_type="refresh",
		expires_at=exp_to_datetime(payload.exp),
	)

	await _store_refresh_token(db, user.id, new_refresh_token)
	try:
		await db.commit()
	except SQLAlchemyError as exc:
		await db.rollback()
		raise ValueError("Unable to refresh token at the moment") from exc

	await _blacklist_token(
		db=db,
		redis=redis,
		jti=payload.jti,
		token_type="refresh",
		expires_at=exp_to_datetime(payload.exp),
		persist_db=False,
	)

	return Token(access_token=new_access_token, refresh_token=new_refresh_token)


async def revoke_token_if_present(db: AsyncSession, redis: Redis, token: str) -> None:
	try:
		payload = await decode_token(token)
	except ValueError:
		return

	await _blacklist_token(
		db=db,
		redis=redis,
		jti=payload.jti,
		token_type=payload.typ,
		expires_at=exp_to_datetime(payload.exp),
	)

	if payload.typ == "refresh":
		token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.jti))
		if token_row is not None and token_row.revoked_at is None:
			token_row.revoked_at = datetime.now(timezone.utc)

	await db.commit()
