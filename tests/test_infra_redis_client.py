import pytest

from api.infra.redis_client import RedisClient
from unittest.mock import AsyncMock
from redis.asyncio import Redis


@pytest.mark.asyncio
async def test_set_and_get():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {}
    # Mockear el cliente interno
    mock_redis = AsyncMock(spec=Redis)

    async def set_func(k, v, ex=None):
        store[k] = v
        return True

    async def get_func(k):
        return store.get(k)

    async def delete_func(k):
        store.pop(k, None)
        return True

    mock_redis.set.side_effect = set_func
    mock_redis.get.side_effect = get_func
    mock_redis.delete.side_effect = delete_func
    r.client = mock_redis
    await r.client.set("foo", "bar")
    val = await r.client.get("foo")
    assert val == "bar"
    await r.client.delete("foo")
    assert await r.client.get("foo") is None


@pytest.mark.asyncio
def test_blacklist_provider_and_check():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {}
    mock_redis = AsyncMock(spec=Redis)

    async def setex_func(key, seconds, value):
        store[key] = value
        return True

    async def get_func(key):
        return store.get(key)

    mock_redis.setex.side_effect = setex_func
    mock_redis.get.side_effect = get_func
    r.client = mock_redis
    # Blacklist provider
    import asyncio

    asyncio.run(r.blacklist_provider("prov", 10))
    assert store["blacklist:prov"] == "1"
    # Check blacklist
    result = asyncio.run(r.is_provider_blacklisted("prov"))
    assert result is True


@pytest.mark.asyncio
def test_increment_and_reset_failure_count():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {}
    mock_redis = AsyncMock(spec=Redis)

    async def incr_func(key):
        store[key] = str(int(store.get(key, "0")) + 1)
        return int(store[key])

    async def expire_func(key, seconds):
        return True

    async def delete_func(key):
        store.pop(key, None)
        return True

    mock_redis.incr.side_effect = incr_func
    mock_redis.expire.side_effect = expire_func
    mock_redis.delete.side_effect = delete_func
    r.client = mock_redis
    # Increment
    import asyncio

    count = asyncio.run(r.increment_failure_count("prov"))
    assert count == 1
    # Reset
    asyncio.run(r.reset_failure_count("prov"))
    assert store.get("failures:prov") is None


@pytest.mark.asyncio
def test_check_rate_limit():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {}
    mock_redis = AsyncMock(spec=Redis)

    async def get_func(key):
        return store.get(key)

    async def setex_func(key, window_seconds, value):
        store[key] = value
        return True

    async def incr_func(key):
        store[key] = int(store.get(key, 0)) + 1
        return store[key]

    mock_redis.get.side_effect = get_func
    mock_redis.setex.side_effect = setex_func
    mock_redis.incr.side_effect = incr_func
    r.client = mock_redis
    import asyncio

    allowed, remaining = asyncio.run(r.check_rate_limit("id", 2, 10))
    assert allowed is True and remaining == 1
    allowed, remaining = asyncio.run(r.check_rate_limit("id", 2, 10))
    assert allowed is True and remaining == 0
    allowed, remaining = asyncio.run(r.check_rate_limit("id", 2, 10))
    assert allowed is False and remaining == 0


@pytest.mark.asyncio
def test_acquire_and_release_slot():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {}
    mock_redis = AsyncMock(spec=Redis)

    async def get_func(key):
        return store.get(key)

    async def incr_func(key):
        store[key] = str(int(store.get(key, "0")) + 1)
        return int(store[key])

    async def expire_func(key, ttl):
        return True

    async def decr_func(key):
        store[key] = str(int(store.get(key, "1")) - 1)
        return int(store[key])

    mock_redis.get.side_effect = get_func
    mock_redis.incr.side_effect = incr_func
    mock_redis.expire.side_effect = expire_func
    mock_redis.decr.side_effect = decr_func
    r.client = mock_redis
    import asyncio

    # Acquire slot (should succeed)
    assert asyncio.run(r.acquire_slot("res", 2)) is True
    # Acquire slot (should succeed)
    assert asyncio.run(r.acquire_slot("res", 2)) is True
    # Acquire slot (should fail)
    assert asyncio.run(r.acquire_slot("res", 2)) is False
    # Release slot
    asyncio.run(r.release_slot("res"))
    assert store["concurrency:res"] == "1"


@pytest.mark.asyncio
def test_get_failure_count():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {"failures:prov": "3"}
    mock_redis = AsyncMock(spec=Redis)

    async def get_func(key):
        return store.get(key)

    mock_redis.get.side_effect = get_func
    r.client = mock_redis
    import asyncio

    count = asyncio.run(r.get_failure_count("prov"))
    assert count == 3


@pytest.mark.asyncio
def test_release_slot():
    r = RedisClient(redis_url="redis://localhost:6379/0")
    store = {"concurrency:res": "2"}
    mock_redis = AsyncMock(spec=Redis)

    async def get_func(key):
        return store.get(key)

    async def decr_func(key):
        store[key] = str(int(store.get(key, "1")) - 1)
        return int(store[key])

    mock_redis.get.side_effect = get_func
    mock_redis.decr.side_effect = decr_func
    r.client = mock_redis
    import asyncio

    asyncio.run(r.release_slot("res"))
    assert store["concurrency:res"] == "1"
