import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal
from app.dependencies import _is_blacklisted
from app.models import User
from app.oauth2 import decode_token

settings = get_settings()
logger = logging.getLogger(__name__)


def _presence_key(user_id: int) -> str:
	return f"presence:user:{user_id}"


async def set_online(redis: Redis, user_id: int) -> None:
	await redis.set(_presence_key(user_id), "online", ex=settings.online_status_ttl_seconds)


async def set_offline(redis: Redis, user_id: int) -> None:
	await redis.delete(_presence_key(user_id))


async def get_online_user_ids(redis: Redis) -> list[int]:
	keys = await redis.keys("presence:user:*")
	user_ids: list[int] = []
	for key in keys:
		try:
			user_ids.append(int(key.split(":")[-1]))
		except ValueError:
			continue
	return sorted(set(user_ids))


async def _authenticate_socket_user(websocket: WebSocket, redis: Redis) -> int:
	token = websocket.query_params.get("token")
	if not token:
		await websocket.close(code=1008, reason="Missing access token")
		raise ValueError("Missing access token")

	try:
		payload = await decode_token(token)
	except (ValueError, JWTError) as exc:
		await websocket.close(code=1008, reason="Invalid token")
		raise ValueError("Invalid token") from exc

	if payload.typ != "access":
		await websocket.close(code=1008, reason="Token type not allowed")
		raise ValueError("Token type not allowed")

	if await _is_blacklisted(redis, payload.jti):
		await websocket.close(code=1008, reason="Token revoked")
		raise ValueError("Token revoked")

	try:
		user_id = int(payload.sub)
	except ValueError as exc:
		await websocket.close(code=1008, reason="Invalid token subject")
		raise ValueError("Invalid token subject") from exc

	async with SessionLocal() as db:
		db: AsyncSession
		user = await db.get(User, user_id)
		if user is None or not user.is_active:
			await websocket.close(code=1008, reason="Inactive user")
			raise ValueError("Inactive user")

	return user_id


async def handle_presence_socket(websocket: WebSocket, redis: Redis) -> None:
	await websocket.accept()

	try:
		user_id = await _authenticate_socket_user(websocket, redis)
	except ValueError as exc:
		logger.debug("Presence websocket authentication failed: %s", exc)
		return

	await set_online(redis, user_id)
	heartbeat_interval = settings.heartbeat_interval_seconds

	try:
		while True:
			try:
				message = await asyncio.wait_for(websocket.receive_text(), timeout=heartbeat_interval)
				if message.lower() in {"pong", "ping", "heartbeat"}:
					await set_online(redis, user_id)
					await websocket.send_json({"type": "heartbeat_ack", "status": "ok"})
				else:
					await websocket.send_json({"type": "echo", "message": message})
			except asyncio.TimeoutError:
				await websocket.send_json({"type": "ping"})
				await set_online(redis, user_id)
	except WebSocketDisconnect:
		logger.debug("Presence websocket disconnected for user_id=%s", user_id)
	except Exception as exc:
		logger.warning("Presence websocket loop error for user_id=%s: %s", user_id, exc)
	finally:
		try:
			await set_offline(redis, user_id)
		except Exception as exc:
			logger.warning("Failed to clear presence state for user_id=%s: %s", user_id, exc)
