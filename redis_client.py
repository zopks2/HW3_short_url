import redis.asyncio as redis
from config import REDIS_HOST, REDIS_PORT

redis_pool = None

def get_redis_pool():
    """Возвращает пул соединений Redis (создает при первом вызове)."""
    global redis_pool
    if redis_pool is None:
        print(f"Initializing Redis connection pool to {REDIS_HOST}:{REDIS_PORT}")
        redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,
            decode_responses=True
        )
    return redis_pool

async def get_redis_connection() -> redis.Redis:
    """Возвращает асинхронное соединение Redis из пула."""
    pool = get_redis_pool()
    return redis.Redis(connection_pool=pool)

async def close_redis_pool():
    """Закрывает пул соединений Redis."""
    global redis_pool
    if redis_pool:
        print("Closing Redis connection pool...")
        await redis_pool.disconnect()
        redis_pool = None
