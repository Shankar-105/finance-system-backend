import fakeredis.aioredis

from app.services.presence_service import get_online_user_ids, set_offline, set_online


async def test_set_online_marks_user_present():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await set_online(redis, 11)

    users = await get_online_user_ids(redis)
    assert users == [11]
    await redis.aclose()


async def test_set_offline_removes_user_presence():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await set_online(redis, 12)
    await set_offline(redis, 12)

    users = await get_online_user_ids(redis)
    assert users == []
    await redis.aclose()


async def test_get_online_user_ids_returns_sorted_unique_values():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await set_online(redis, 44)
    await set_online(redis, 7)
    await set_online(redis, 44)

    users = await get_online_user_ids(redis)
    assert users == [7, 44]
    await redis.aclose()


async def test_presence_ttl_is_applied():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await set_online(redis, 21)

    ttl = await redis.ttl("presence:user:21")
    assert ttl > 0
    await redis.aclose()
