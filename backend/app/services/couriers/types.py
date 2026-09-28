"""Result types shared by all courier integrations.

Courier calls never raise to the caller: every failure (missing credentials,
timeouts, HTTP errors, unreadable responses) is returned as a result with a
non-"ok" state and a user-facing message, so one broken API never breaks a page.
"""

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

STATE_OK = "ok"
STATE_NOT_FOUND = "not_found"  # the carrier answered but does not know this number
STATE_UNAVAILABLE = "unavailable"  # the carrier could not be asked or gave an error
STATE_NOT_IMPLEMENTED = "not_implemented"  # no integration / not configured for this carrier


@dataclass(frozen=True)
class Place:
    suburb: str
    state: str
    postcode: str


@dataclass(frozen=True)
class Parcel:
    """One carton, in the units carriers expect (cm, kg)."""

    length_cm: int
    width_cm: int
    height_cm: int
    weight_kg: Decimal
    item_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "length_cm": self.length_cm,
            "width_cm": self.width_cm,
            "height_cm": self.height_cm,
            "weight_kg": str(self.weight_kg),
            "item_count": self.item_count,
        }


@dataclass(frozen=True)
class TrackingEvent:
    description: str
    location: str | None
    occurred_at: str | None  # ISO 8601 as reported by the carrier


@dataclass
class TrackingResult:
    tracking_no: str
    carrier: str
    state: str
    status: str | None = None
    last_update: str | None = None
    last_location: str | None = None
    events: list[TrackingEvent] = field(default_factory=list)
    message: str | None = None
    error_code: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackingResult":
        events = [TrackingEvent(**e) for e in data.get("events", [])]
        return cls(**{**data, "events": events})


@dataclass(frozen=True)
class QuoteResult:
    carrier: str
    state: str
    service_code: str | None = None
    service_name: str | None = None
    fee_ex_gst: Decimal | None = None
    fee_incl_gst: Decimal | None = None
    message: str | None = None
    source: str | None = None
