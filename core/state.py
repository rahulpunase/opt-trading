import json
import os
from typing import Optional

import redis


class StrategyState:
    def __init__(self, strategy_name: str, redis_client: redis.Redis):
        self._name = strategy_name
        self._r = redis_client

    def _key(self, key: str) -> str:
        return f"{self._name}:{key}"

    def get(self, key: str) -> Optional[str]:
        val = self._r.get(self._key(key))
        return val.decode() if val else None

    def set(self, key: str, value, ex: int = None):
        self._r.set(self._key(key), value, ex=ex)

    def delete(self, key: str):
        self._r.delete(self._key(key))

    def hget(self, name: str, field: str):
        val = self._r.hget(self._key(name), field)
        return val.decode() if val else None

    def hset(self, name: str, field: str, value):
        self._r.hset(self._key(name), field, value)

    def hdel(self, name: str, field: str):
        self._r.hdel(self._key(name), field)

    def hgetall(self, name: str) -> dict:
        raw = self._r.hgetall(self._key(name))
        return {k.decode(): v.decode() for k, v in raw.items()}

    def expire(self, key: str, seconds: int):
        self._r.expire(self._key(key), seconds)

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key)
        return int(val) if val is not None else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        val = self.get(key)
        return float(val) if val is not None else default

    def get_json(self, key: str, default=None):
        val = self.get(key)
        if val is None:
            return default
        return json.loads(val)

    def set_json(self, key: str, value, ex: int = None):
        self.set(key, json.dumps(value), ex=ex)

    # Portfolio-level keys (not namespaced)
    def portfolio_get(self, key: str):
        val = self._r.get(f"portfolio:{key}")
        return val.decode() if val else None

    def portfolio_set(self, key: str, value, ex: int = None):
        self._r.set(f"portfolio:{key}", value, ex=ex)

    def portfolio_get_json(self, key: str, default=None):
        val = self.portfolio_get(key)
        if val is None:
            return default
        return json.loads(val)

    def portfolio_set_json(self, key: str, value, ex: int = None):
        self.portfolio_set(key, json.dumps(value), ex=ex)



def make_redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
    )
