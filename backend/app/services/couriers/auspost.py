"""Australia Post / StarTrack Shipping & Tracking API.

Docs: https://developers.auspost.com.au/apis/shipping-and-tracking/reference/track-items
- Auth: HTTP Basic (API key : password) plus an "Account-Number" header.
  StarTrack consignments (e.g. 2FWZ..., RBXZ...) use the 8-digit StarTrack account.
- Tracking: GET /track?tracking_ids=a,b,... (max 10 per request, 10 requests/minute).
- Pricing:  POST /prices/shipments.
- The testbed returns simulated tracking data (the same sample history for any number),
  so results from a /test/ base URL are labelled as simulated.

Concurrency: batches run concurrently; the one-by-one fallback after a rejected
batch is limited to _MAX_PARALLEL requests at a time to respect the rate limit.
"""

import asyncio
import base64
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings
from app.models import CARRIER_STARTRACK
from app.services.couriers.types import (
    STATE_NOT_FOUND,
    STATE_OK,
    STATE_UNAVAILABLE,
    Parcel,
    Place,
    QuoteResult,
    TrackingEvent,
    TrackingResult,
)

log = logging.getLogger(__name__)

MAX_IDS_PER_REQUEST = 10
_MAX_PARALLEL = 3
# Per-ID errors that mean "this number is unknown" rather than "the service failed"
_NOT_FOUND_CODES = {"ESB-10001", "ESB-10002", "51104"}
_PRODUCT_NAMES = {"EXP": "StarTrack Express", "PRM": "StarTrack Premium", "FPP": "StarTrack Fixed Price Premium"}


class AusPostClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http
        self._base_url = settings.auspost_base_url.rstrip("/")
        self._limit = asyncio.Semaphore(_MAX_PARALLEL)

    @property
    def configured(self) -> bool:
        s = self._settings
        return bool(s.auspost_api_key and s.auspost_password and s.auspost_account_number_startrack)

    @property
    def source(self) -> str:
        if "/test/" in f"{self._base_url}/":
            return "Australia Post testbed (simulated data)"
        return "Australia Post"

    def _headers(self) -> dict[str, str]:
        s = self._settings
        token = base64.b64encode(f"{s.auspost_api_key}:{s.auspost_password}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Account-Number": s.auspost_account_number_startrack,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ tracking

    async def track(self, tracking_nos: list[str]) -> dict[str, TrackingResult]:
        if not self.configured:
            return {
                n: self._unavailable(n, "Australia Post credentials are not configured", "NOT_CONFIGURED")
                for n in tracking_nos
            }
        chunks = [
            tracking_nos[start : start + MAX_IDS_PER_REQUEST]
            for start in range(0, len(tracking_nos), MAX_IDS_PER_REQUEST)
        ]
        results: dict[str, TrackingResult] = {}
        for chunk_results in await asyncio.gather(*(self._track_chunk(c) for c in chunks)):
            results.update(chunk_results)
        return results

    async def _track_chunk(self, chunk: list[str]) -> dict[str, TrackingResult]:
        try:
            async with self._limit:
                response = await self._http.get(
                    f"{self._base_url}/track",
                    params={"tracking_ids": ",".join(chunk)},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            log.warning("AusPost tracking request failed: %s", type(exc).__name__)
            return {n: self._unavailable(n, "Could not reach Australia Post", "NETWORK") for n in chunk}

        if response.status_code == 400 and len(chunk) > 1:
            # A single malformed ID (or an Australia Post ID mixed with StarTrack IDs,
            # error 51103) rejects the whole request; retry one by one so only the bad one fails.
            results: dict[str, TrackingResult] = {}
            for single in await asyncio.gather(*(self._track_chunk([n]) for n in chunk)):
                results.update(single)
            return results

        if response.status_code != 200:
            code, message = _error_from_response(response)
            text = f"Australia Post returned HTTP {response.status_code}: {message}"
            log.warning("AusPost tracking error %s %s", response.status_code, code)
            state = STATE_NOT_FOUND if response.status_code == 400 else STATE_UNAVAILABLE
            return {
                n: TrackingResult(
                    tracking_no=n,
                    carrier=CARRIER_STARTRACK,
                    state=state,
                    message=text,
                    error_code=code,
                    source=self.source,
                )
                for n in chunk
            }

        try:
            body = response.json()
        except ValueError:
            return {n: self._unavailable(n, "Australia Post returned an unreadable response", "BAD_RESPONSE") for n in chunk}

        results: dict[str, TrackingResult] = {}
        for item in body.get("tracking_results", []):
            tracking_no = str(item.get("tracking_id", "")).strip()
            if tracking_no in chunk:
                results[tracking_no] = self._parse_result(tracking_no, item)
        for n in chunk:
            if n not in results:
                results[n] = TrackingResult(
                    tracking_no=n,
                    carrier=CARRIER_STARTRACK,
                    state=STATE_NOT_FOUND,
                    message="Australia Post returned no result for this tracking number",
                    source=self.source,
                )
        return results

    def _parse_result(self, tracking_no: str, item: dict[str, Any]) -> TrackingResult:
        errors = item.get("errors") or []
        if errors:
            code = str(errors[0].get("code") or errors[0].get("error_code") or "")
            name = errors[0].get("name") or errors[0].get("message") or "Unknown error"
            return TrackingResult(
                tracking_no=tracking_no,
                carrier=CARRIER_STARTRACK,
                state=STATE_NOT_FOUND if code in _NOT_FOUND_CODES else STATE_UNAVAILABLE,
                message=f"Australia Post: {name}",
                error_code=code or None,
                source=self.source,
            )

        consignment = item.get("consignment") or {}
        events = _collect_events(item)
        status = consignment.get("status") or item.get("status") or (events[0].description if events else None)
        return TrackingResult(
            tracking_no=tracking_no,
            carrier=CARRIER_STARTRACK,
            state=STATE_OK,
            status=status,
            last_update=events[0].occurred_at if events else None,
            last_location=events[0].location if events else None,
            events=events,
            source=self.source,
        )

    def _unavailable(self, tracking_no: str, message: str, code: str | None) -> TrackingResult:
        return TrackingResult(
            tracking_no=tracking_no,
            carrier=CARRIER_STARTRACK,
            state=STATE_UNAVAILABLE,
            message=message,
            error_code=code,
            source=self.source,
        )

    # ------------------------------------------------------------------ pricing

    async def quote(self, parcel: Parcel, origin: Place, destination: Place) -> QuoteResult:
        product_id = self._settings.startrack_product_id
        service_name = _PRODUCT_NAMES.get(product_id, product_id)
        if not self.configured:
            return self._quote_unavailable("Australia Post credentials are not configured", product_id, service_name)

        payload = {
            "shipments": [
                {
                    "from": {"suburb": origin.suburb, "state": origin.state, "postcode": origin.postcode},
                    "to": {"suburb": destination.suburb, "state": destination.state, "postcode": destination.postcode},
                    "items": [
                        {
                            "product_id": product_id,
                            "length": parcel.length_cm,
                            "width": parcel.width_cm,
                            "height": parcel.height_cm,
                            "weight": float(parcel.weight_kg),
                            "packaging_type": "CTN",
                        }
                    ],
                }
            ]
        }
        try:
            async with self._limit:
                response = await self._http.post(
                    f"{self._base_url}/prices/shipments", json=payload, headers=self._headers()
                )
        except httpx.HTTPError as exc:
            log.warning("AusPost pricing request failed: %s", type(exc).__name__)
            return self._quote_unavailable("Could not reach Australia Post", product_id, service_name)

        if response.status_code != 200:
            code, message = _error_from_response(response)
            return self._quote_unavailable(
                f"Australia Post returned HTTP {response.status_code}: {message} ({code})", product_id, service_name
            )
        try:
            summary = response.json()["shipments"][0]["shipment_summary"]
            fee_incl = Decimal(str(summary["total_cost"]))
            fee_ex = Decimal(str(summary["total_cost_ex_gst"]))
        except (ValueError, KeyError, IndexError, TypeError, InvalidOperation):
            return self._quote_unavailable("Australia Post returned an unreadable price", product_id, service_name)

        return QuoteResult(
            carrier=CARRIER_STARTRACK,
            state=STATE_OK,
            service_code=product_id,
            service_name=service_name,
            fee_ex_gst=fee_ex,
            fee_incl_gst=fee_incl,
            source=self.source.replace("simulated data", "test rates"),
        )

    def _quote_unavailable(self, message: str, product_id: str, service_name: str) -> QuoteResult:
        return QuoteResult(
            carrier=CARRIER_STARTRACK,
            state=STATE_UNAVAILABLE,
            service_code=product_id,
            service_name=service_name,
            message=message,
            source=self.source,
        )


def _error_from_response(response: httpx.Response) -> tuple[str | None, str]:
    """AusPost uses two error shapes: {code, name, message} for business errors and
    {error_code, error_name, message} from the API gateway (401, 429)."""
    try:
        errors = response.json().get("errors") or []
    except (ValueError, AttributeError):
        errors = []
    if errors:
        first = errors[0]
        code = first.get("code") or first.get("error_code")
        message = first.get("message") or first.get("name") or first.get("error_name") or "Unknown error"
        return (str(code) if code else None), message
    return None, response.reason_phrase or "Unknown error"


def _collect_events(item: dict[str, Any]) -> list[TrackingEvent]:
    """Merge consignment-level and article-level events, newest first, without duplicates.
    Handles both the StarTrack shape (trackable_items[].events) and the Australia Post
    shape (trackable_items[].items[].events)."""
    raw: list[dict[str, Any]] = list((item.get("consignment") or {}).get("events") or [])
    for trackable in item.get("trackable_items") or []:
        raw.extend(trackable.get("events") or [])
        for article in trackable.get("items") or []:
            raw.extend(article.get("events") or [])

    seen: set[tuple[str, str, str]] = set()
    events: list[TrackingEvent] = []
    for e in raw:
        key = (e.get("date") or "", e.get("description") or "", e.get("location") or "")
        if key in seen:
            continue
        seen.add(key)
        events.append(
            TrackingEvent(
                description=e.get("description") or "Unknown event",
                location=e.get("location") or None,
                occurred_at=e.get("date") or None,
            )
        )
    events.sort(key=lambda e: _sort_key(e.occurred_at), reverse=True)
    return events


def _sort_key(value: str | None) -> float:
    try:
        return datetime.fromisoformat(value).timestamp() if value else 0.0
    except ValueError:
        return 0.0
