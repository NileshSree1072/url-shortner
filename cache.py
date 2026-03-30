import os
import json
from upstash_redis import Redis
from dotenv import load_dotenv

load_dotenv()

redis = None

redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if redis_url and redis_token:
    redis = Redis(url=redis_url, token=redis_token)

def get_cached_url(code: str):
    if redis is None:
        return None

    try:
        value = redis.get(code)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    except Exception:
        return None

def cache_url(code: str, value, ttl: int = 86400):
    if redis is None:
        return

    try:
        payload = json.dumps(value) if isinstance(value, (dict, list)) else value
        redis.set(code, payload, ex=ttl)
    except Exception:
        return

def delete_cache(code: str):
    if redis is None:
        return

    try:
        redis.delete(code)
    except Exception:
        return
