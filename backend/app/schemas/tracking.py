from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TrackingState = Literal["ok", "not_found", "unavailable", "not_implemented"]


class TrackingEventOut(BaseModel):
    description: str
    location: str | None
    occurred_at: str | None  # ISO 8601 as reported by the carrier (TNT has no time zone)


class TrackingOut(BaseModel):
    tracking_ref: str | None  # "Track 1"; None for ad-hoc lookups
    tracking_no: str
    carrier: str
    state: TrackingState
    status: str | None
    last_update: str | None
    last_location: str | None
    events: list[TrackingEventOut]  # newest first
    message: str | None  # reason when state != "ok"
    error_code: str | None
    source: str | None  # e.g. "Australia Post testbed (simulated data)"
    fetched_at: datetime
    cached: bool


class OrderTrackingOut(BaseModel):
    order_no: str
    shipments: list[TrackingOut]
