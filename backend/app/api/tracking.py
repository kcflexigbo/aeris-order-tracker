import re
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CacheDep, CouriersDep, DbSession
from app.schemas import OrderTrackingOut, TrackingEventOut, TrackingOut
from app.services.orders import load_order, order_shipments
from app.services.tracking import TrackingLookup, get_tracking

router = APIRouter(tags=["tracking"])

MAX_LOOKUP_IDS = 10
_ID_SPLIT = re.compile(r"[\s,]+")


def _to_out(lookup: TrackingLookup, tracking_ref: str | None) -> TrackingOut:
    r = lookup.result
    return TrackingOut(
        tracking_ref=tracking_ref,
        tracking_no=r.tracking_no,
        carrier=r.carrier,
        state=r.state,
        status=r.status,
        last_update=r.last_update,
        last_location=r.last_location,
        events=[
            TrackingEventOut(description=e.description, location=e.location, occurred_at=e.occurred_at)
            for e in r.events
        ],
        message=r.message,
        error_code=r.error_code,
        source=r.source,
        fetched_at=lookup.fetched_at,
        cached=lookup.cached,
    )


@router.get("/api/orders/{order_no}/tracking", response_model=OrderTrackingOut)
async def get_order_tracking(
    order_no: str,
    db: DbSession,
    couriers: CouriersDep,
    cache: CacheDep,
    refresh: bool = False,
) -> OrderTrackingOut:
    """Tracking for every shipment of an order, fetched concurrently; cached in Redis."""
    order = await load_order(db, order_no)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_no} not found")
    shipments = order_shipments(order)
    lookups = await get_tracking([(s.carrier, s.tracking_no) for s in shipments], couriers, cache, refresh)
    return OrderTrackingOut(
        order_no=order.order_no,
        shipments=[_to_out(lookups[(s.carrier, s.tracking_no)], s.tracking_ref) for s in shipments],
    )


@router.get("/api/tracking", response_model=list[TrackingOut])
async def lookup_tracking(
    carrier: Literal["STARTRACK", "TNT"],
    ids: Annotated[str, Query(description="Comma- or space-separated tracking numbers (max 10)")],
    couriers: CouriersDep,
    cache: CacheDep,
    refresh: bool = False,
) -> list[TrackingOut]:
    """Ad-hoc lookup, e.g. for the extra AusPost test numbers in the brief."""
    tracking_nos = list(dict.fromkeys(n for n in _ID_SPLIT.split(ids.strip()) if n))
    if not tracking_nos:
        raise HTTPException(status_code=422, detail="Provide at least one tracking number")
    if len(tracking_nos) > MAX_LOOKUP_IDS:
        raise HTTPException(status_code=422, detail=f"At most {MAX_LOOKUP_IDS} tracking numbers per lookup")
    if any(len(n) > 64 for n in tracking_nos):
        raise HTTPException(status_code=422, detail="Tracking numbers must be at most 64 characters")
    lookups = await get_tracking([(carrier, n) for n in tracking_nos], couriers, cache, refresh)
    return [_to_out(lookups[(carrier, n)], None) for n in tracking_nos]
