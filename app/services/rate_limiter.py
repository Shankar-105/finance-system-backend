from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.db import get_redis
from app.oauth2 import decode_token


def fixed_window_rate_limiter(
	key_prefix: str,
	max_requests: int,
	window_seconds: int,
) -> Callable:
	async def dependency(
		request: Request,
		redis: Redis = Depends(get_redis),
	) -> None:
		client_ip = request.client.host if request.client else "unknown"
		identity = f"ip:{client_ip}"

		authorization = request.headers.get("authorization", "")
		if authorization.lower().startswith("bearer "):
			token = authorization.split(" ", 1)[1].strip()
			try:
				payload = await decode_token(token)
				if payload.typ == "access" and payload.sub:
					identity = f"user:{payload.sub}"
			except ValueError:
				# Fall back to IP-based limiting for invalid/expired tokens.
				pass

		path_key = request.url.path.replace("/", "_")
		key = f"{key_prefix}:{identity}:{path_key}"

		try:
			current = await redis.incr(key)
			if current == 1:
				await redis.expire(key, window_seconds)

			if current > max_requests:
				retry_after = await redis.ttl(key)
				raise HTTPException(
					status_code=429,
					detail="Rate limit exceeded",
					headers={"Retry-After": str(max(retry_after, 1))},
				)
		except RedisError as exc:
			raise HTTPException(
				status_code=503,
				detail="Rate limiter unavailable",
			) from exc

	return dependency
