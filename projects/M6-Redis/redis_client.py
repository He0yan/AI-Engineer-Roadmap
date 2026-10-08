import os
import redis
from redis import ConnectionPool

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# 创建连接池，整个应用共用一个池
pool = ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,   # 返回 str 而不是 bytes
    max_connections=20,
)

def get_redis() -> redis.Redis:
    """
    FastAPI 依赖注入用。
    每次请求返回一个使用共享连接池的 Redis 客户端。
    """
    return redis.Redis(connection_pool=pool)