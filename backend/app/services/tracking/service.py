import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import CARRIER_STARTRACK, CARRIER_TNT
from app.services.couriers import (
    STATE_NOT_FOUND,
    STATE_NOT_IMPLEMENTED,
    STATE_OK,
    Couriers,
    TrackingResult,
)
from app.services.tracking.cache import CachedTracking, TrackingCache

# Failures are not cached, so the next page load tries the carrier again.
_CACHEABLE_STATES = {STATE_OK, STATE_NOT_FOUND}


@dataclass(frozen=True)
class TrackingLookup:
    result: TrackingResult
    fetched_at: datetime
    cached: bool


async def get_tracking(
    requests: list[tuple[str, str]],
    couriers: Couriers,
    cache: TrackingCache,
    refresh: bool = False,
) -> dict[tuple[str, str], TrackingLookup]:
    """Look up (carrier, tracking_no) pairs: cache first (unless refresh), then
    every carrier concurrently (StarTrack as one batch, TNT one request per consignment)."""
    by_carrier: dict[str, list[str]] = defaultdict(list)
    for carrier, tracking_no in dict.fromkeys(requests):
        by_carrier[carrier].append(tracking_no)
    carriers = list(by_carrier)

    lookups: dict[tuple[str, str], TrackingLookup] = {}
    missing: dict[str, list[str]] = dict(by_carrier)
    if not refresh:
        hits_per_carrier: list[dict[str, CachedTracking]] = await asyncio.gather(
            *(cache.get_many(c, by_carrier[c]) for c in carriers)
        )
        for carrier, hits in zip(carriers, hits_per_carrier):
            for tracking_no, hit in hits.items():
                lookups[(carrier, tracking_no)] = TrackingLookup(hit.result, hit.fetched_at, cached=True)
            missing[carrier] = [n for n in by_carrier[carrier] if n not in hits]

    to_fetch = {c: nos for c, nos in missing.items() if nos}
    if not to_fetch:
        return lookups

    fetched_at = datetime.now(UTC)
    fetched: list[list[TrackingResult]] = await asyncio.gather(
        *(_fetch(couriers, c, nos) for c, nos in to_fetch.items())
    )
    results = [r for per_carrier in fetched for r in per_carrier]
    for result in results:
        lookups[(result.carrier, result.tracking_no)] = TrackingLookup(result, fetched_at, cached=False)
    await cache.set_many([r for r in results if r.state in _CACHEABLE_STATES], fetched_at)
    return lookups


async def _fetch(couriers: Couriers, carrier: str, tracking_nos: list[str]) -> list[TrackingResult]:
    if carrier == CARRIER_STARTRACK:
        return list((await couriers.auspost.track(tracking_nos)).values())
    if carrier == CARRIER_TNT:
        return await couriers.tnt.track_many(tracking_nos)
    return [
        TrackingResult(
            tracking_no=n,
            carrier=carrier,
            state=STATE_NOT_IMPLEMENTED,
            message="No tracking integration for this logistics company",
        )
        for n in tracking_nos
    ]
