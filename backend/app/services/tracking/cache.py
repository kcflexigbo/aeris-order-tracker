"""Redis cache for tracking results.

Tracking data is short-lived and AusPost allows only 10 requests/minute, so
results are cached with a TTL. The cache is optional: if Redis is unreachable
every call falls through to the carrier and the app keeps working.
After a Redis failure the cache is skipped for a short back-off period, so a
missing Redis does not add a connection timeout to every request.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime

import redis
import redis.asyncio as aioredis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.services.couriers import TrackingResult

log = logging.getLogger(__name__)

_BACKOFF_SECONDS = 30.0
# redis-py wraps most failures in RedisError, but a refused/timed-out socket can
# surface as a plain OSError or TimeoutError depending on the platform.
_CACHE_ERRORS = (redis.RedisError, OSError, TimeoutError)


@dataclass(frozen=True)
class CachedTracking:
    result: TrackingResult
    fetched_at: datetime


class TrackingCache:
    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._down_until = 0.0
        self._client = aioredis.Redis.from_url(
            redis_url,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
            retry=Retry(NoBackoff(), 0),  # a cache miss is cheap; never retry
            decode_responses=True,
        )

    @staticmethod
    def key(carrier: str, tracking_no: str) -> str:
        return f"tracking:{carrier}:{tracking_no}"

    def _available(self) -> bool:
        return time.monotonic() >= self._down_until

    def _mark_down(self, exc: BaseException, action: str) -> None:
        self._down_until = time.monotonic() + _BACKOFF_SECONDS
        log.warning(
            "Tracking cache %s failed (%s); skipping Redis for %.0fs",
            action,
            type(exc).__name__,
            _BACKOFF_SECONDS,
        )

    async def get_many(self, carrier: str, tracking_nos: list[str]) -> dict[str, CachedTracking]:
        if not tracking_nos or not self._available():
            return {}
        try:
            values = await self._client.mget([self.key(carrier, n) for n in tracking_nos])
        except _CACHE_ERRORS as exc:
            self._mark_down(exc, "read")
            return {}
        found: dict[str, CachedTracking] = {}
        for tracking_no, raw in zip(tracking_nos, values):
            if raw is None:
                continue
            try:
                data = json.loads(raw)
                found[tracking_no] = CachedTracking(
                    result=TrackingResult.from_dict(data["result"]),
                    fetched_at=datetime.fromisoformat(data["fetched_at"]),
                )
            except (ValueError, KeyError, TypeError):
                continue  # corrupt or old-format entry: treat as a miss
        return found

    async def set_many(self, results: list[TrackingResult], fetched_at: datetime) -> None:
        """Write several results in one round trip (pipeline)."""
        if not results or not self._available():
            return
        pipe = self._client.pipeline(transaction=False)
        for result in results:
            payload = json.dumps({"result": result.to_dict(), "fetched_at": fetched_at.isoformat()})
            pipe.set(self.key(result.carrier, result.tracking_no), payload, ex=self._ttl)
        try:
            await pipe.execute()
        except _CACHE_ERRORS as exc:
            self._mark_down(exc, "write")

    async def ping(self) -> bool:
        """Health check; always tries Redis, ignoring the back-off."""
        try:
            ok = bool(await self._client.ping())
        except _CACHE_ERRORS:
            return False
        self._down_until = 0.0
        return ok

    async def close(self) -> None:
        await self._client.aclose()
