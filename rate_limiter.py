import time
from cache import redis

def is_rate_limited(ip: str, limit: int = 10, window: int = 60):
    if redis is None:
        return False

    key = f"rl:{ip}"
    now = time.time()

    try:
        # Remove old requests
        redis.zremrangebyscore(key, 0, now - window)

        # Add current request
        redis.zadd(key, {str(now): now})

        # Count requests
        count = redis.zcard(key)

        # Set expiry
        redis.expire(key, window)
    except Exception:
        # If Redis is unavailable, keep the API usable instead of returning 500.
        return False

    return count > limit
