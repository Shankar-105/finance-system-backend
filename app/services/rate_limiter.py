from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.db import get_redis


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
		path_key = request.url.path.replace("/", "_")
		key = f"{key_prefix}:{client_ip}:{path_key}"

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

	return dependency
