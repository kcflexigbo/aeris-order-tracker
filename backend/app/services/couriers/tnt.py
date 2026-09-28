"""TNT Australia integrations.

Tracking: the legacy consignment-history weblink
    GET https://www.tntexpress.com.au/InterAction/ASPs/CnmHxAS.asp?<connote>
returns an HTML table (Status | Date | Time | Depot). There is no JSON/XML tracking
API for TNT Australia domestic consignments, so the table is parsed. The page needs
no credentials and does not check that the consignment belongs to us.

Pricing: Rated Transit Times (RTT)
    POST <TNT_RTT_URL> (form fields Username, Password, Version=2, XMLRequest)
The XMLRequest value must be URL-encoded before form encoding (i.e. double-encoded);
a single-encoded request makes the server return an ASP.NET error page.
Suburb and postcode are validated together (broken rule 590/591).
"""

import asyncio
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import quote
from xml.etree import ElementTree
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings
from app.models import CARRIER_TNT
from app.services.couriers.types import (
    STATE_NOT_FOUND,
    STATE_NOT_IMPLEMENTED,
    STATE_OK,
    STATE_UNAVAILABLE,
    Parcel,
    Place,
    QuoteResult,
    TrackingEvent,
    TrackingResult,
)
from app.services.pricing import GST_RATE, round_money

log = logging.getLogger(__name__)

SYDNEY = ZoneInfo("Australia/Sydney")
TRACKING_SOURCE = "TNT consignment history (public weblink)"
_CONNOTE_RE = re.compile(r"^[A-Za-z0-9]{6,20}$")
_HISTORY_HEADER = ["status", "date", "time", "depot"]
_RULE_NOT_A_BUSINESS_DAY = "475"
_MAX_DATE_ATTEMPTS = 4


class TntClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http

    # ------------------------------------------------------------------ tracking

    async def track_many(self, connotes: list[str]) -> list[TrackingResult]:
        """The weblink takes one consignment per request; look them up concurrently."""
        return list(await asyncio.gather(*(self.track(c) for c in connotes)))

    async def track(self, connote: str) -> TrackingResult:
        if not _CONNOTE_RE.match(connote):
            return TrackingResult(
                tracking_no=connote,
                carrier=CARRIER_TNT,
                state=STATE_NOT_FOUND,
                message="Not a valid TNT consignment number (letters and digits only)",
                error_code="INVALID_CONNOTE",
                source=TRACKING_SOURCE,
            )
        try:
            response = await self._http.get(f"{self._settings.tnt_tracking_url}?{connote}")
        except httpx.HTTPError as exc:
            log.warning("TNT tracking request failed: %s", type(exc).__name__)
            return self._unavailable(connote, "Could not reach TNT", "NETWORK")
        if response.status_code != 200:
            return self._unavailable(connote, f"TNT returned HTTP {response.status_code}", str(response.status_code))

        events = parse_history_html(response.text)
        if not events:
            if "no data" in response.text.lower():
                return TrackingResult(
                    tracking_no=connote,
                    carrier=CARRIER_TNT,
                    state=STATE_NOT_FOUND,
                    message="TNT has no history for this consignment",
                    source=TRACKING_SOURCE,
                )
            return self._unavailable(connote, "TNT tracking page format was not recognised", "BAD_RESPONSE")

        latest = events[0]
        return TrackingResult(
            tracking_no=connote,
            carrier=CARRIER_TNT,
            state=STATE_OK,
            status=latest.description,
            last_update=latest.occurred_at,
            last_location=latest.location,
            events=events,
            source=TRACKING_SOURCE,
        )

    def _unavailable(self, connote: str, message: str, code: str | None) -> TrackingResult:
        return TrackingResult(
            tracking_no=connote,
            carrier=CARRIER_TNT,
            state=STATE_UNAVAILABLE,
            message=message,
            error_code=code,
            source=TRACKING_SOURCE,
        )

    # ------------------------------------------------------------------ pricing

    @property
    def rtt_configured(self) -> bool:
        s = self._settings
        return bool(s.tnt_rtt_url and s.tnt_uat_username and s.tnt_uat_password and s.tnt_uat_account)

    @property
    def quote_source(self) -> str:
        return "TNT RTT (UAT test rates)" if "uat." in self._settings.tnt_rtt_url else "TNT RTT"

    async def quote(self, parcel: Parcel, origin: Place, destination: Place) -> QuoteResult:
        if not self.rtt_configured:
            return QuoteResult(
                carrier=CARRIER_TNT,
                state=STATE_NOT_IMPLEMENTED,
                message="TNT RTT credentials are not configured",
            )

        shipping_date = next_business_day(datetime.now(SYDNEY).date())
        # Sequential on purpose: each retry depends on the previous answer.
        for _ in range(_MAX_DATE_ATTEMPTS):
            result = await self._quote_once(parcel, origin, destination, shipping_date)
            if result.error_code != _RULE_NOT_A_BUSINESS_DAY:
                return result.quote
            # public holiday: TNT rejects the date, try the next business day
            shipping_date = next_business_day(shipping_date)
        return result.quote

    async def _quote_once(
        self, parcel: Parcel, origin: Place, destination: Place, shipping_date: date
    ) -> "_Attempt":
        s = self._settings
        xml = build_rtt_request(parcel, origin, destination, shipping_date, s.tnt_uat_account)
        form = {
            "Username": s.tnt_uat_username,
            "Password": s.tnt_uat_password,
            "Version": "2",
            "XMLRequest": quote(xml),  # encoded once here, again by the form encoder
        }
        try:
            response = await self._http.post(s.tnt_rtt_url, data=form)
        except httpx.HTTPError as exc:
            log.warning("TNT RTT request failed: %s", type(exc).__name__)
            return _Attempt(self._quote_unavailable("Could not reach TNT RTT"))
        if response.status_code != 200:
            return _Attempt(self._quote_unavailable(f"TNT RTT returned HTTP {response.status_code}"))

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError:
            return _Attempt(self._quote_unavailable("TNT RTT returned an unreadable response"))

        # Transport errors: <response><error><code>004</code><description>...</description></error></response>
        for error in _find_all(root, "error"):
            code, text = _child_text(error, "code"), _child_text(error, "description")
            return _Attempt(self._quote_unavailable(f"TNT RTT error {code}: {text}"), code)

        # Business-rule errors, e.g. 590/591 invalid suburb+postcode, 475 not a business day
        for rule in _find_all(root, "brokenRule"):
            code, text = _child_text(rule, "code"), _child_text(rule, "description")
            return _Attempt(self._quote_unavailable(f"TNT RTT rule {code}: {' '.join((text or '').split())}"), code)

        offers = []
        for product in _find_all(root, "ratedProduct"):
            try:
                price = Decimal(_child_text(product, "price") or "")
            except InvalidOperation:
                continue
            offers.append((_child_text(product, "code"), _child_text(product, "description"), price))
        if not offers:
            return _Attempt(self._quote_unavailable("TNT RTT returned no services for this route"))

        wanted = s.tnt_service_code
        chosen = next((o for o in offers if o[0] == wanted), None)
        note = None
        if chosen is None:
            chosen = min(offers, key=lambda o: o[2])
            note = f"Service {wanted} was not offered; the cheapest service was used"
        code, name, price = chosen
        if s.tnt_price_includes_gst:
            fee_incl, fee_ex = price, round_money(price / (1 + GST_RATE))
        else:
            fee_ex, fee_incl = price, round_money(price * (1 + GST_RATE))
        return _Attempt(
            QuoteResult(
                carrier=CARRIER_TNT,
                state=STATE_OK,
                service_code=code,
                service_name=f"TNT {name}" if name else code,
                fee_ex_gst=round_money(fee_ex),
                fee_incl_gst=round_money(fee_incl),
                message=note,
                source=self.quote_source,
            )
        )

    def _quote_unavailable(self, message: str) -> QuoteResult:
        return QuoteResult(carrier=CARRIER_TNT, state=STATE_UNAVAILABLE, message=message, source=self.quote_source)


class _Attempt:
    def __init__(self, quote: QuoteResult, error_code: str | None = None) -> None:
        self.quote = quote
        self.error_code = error_code


def next_business_day(day: date) -> date:
    day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def build_rtt_request(parcel: Parcel, origin: Place, destination: Place, shipping_date: date, account: str) -> str:
    now = datetime.now(SYDNEY).strftime("%Y-%m-%dT%H:%M:%S")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<enquiry xmlns="http://www.tntexpress.com.au">'
        "<ratedTransitTimeEnquiry><cutOffTimeEnquiry>"
        f"<collectionAddress>{_address_xml(origin)}</collectionAddress>"
        f"<deliveryAddress>{_address_xml(destination)}</deliveryAddress>"
        f"<shippingDate>{shipping_date.isoformat()}</shippingDate>"
        f"<userCurrentLocalDateTime>{now}</userCurrentLocalDateTime>"
        "<dangerousGoods><dangerous>false</dangerous></dangerousGoods>"
        '<packageLines packageType="N"><packageLine>'
        "<numberOfPackages>1</numberOfPackages>"
        f'<dimensions unit="cm"><length>{parcel.length_cm}</length>'
        f"<width>{parcel.width_cm}</width><height>{parcel.height_cm}</height></dimensions>"
        f'<weight unit="kg"><weight>{parcel.weight_kg}</weight></weight>'
        "</packageLine></packageLines>"
        "</cutOffTimeEnquiry>"
        f"<termsOfPayment><senderAccount>{escape(account)}</senderAccount><payer>S</payer></termsOfPayment>"
        "</ratedTransitTimeEnquiry></enquiry>"
    )


def _address_xml(place: Place) -> str:
    return (
        f"<suburb>{escape(place.suburb)}</suburb>"
        f"<postCode>{escape(place.postcode)}</postCode>"
        f"<state>{escape(place.state)}</state>"
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_all(root: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [el for el in root.iter() if _local_name(el.tag) == name]


def _child_text(element: ElementTree.Element, name: str) -> str | None:
    for el in element.iter():
        if _local_name(el.tag) == name and el.text is not None:
            return el.text.strip()
    return None


class _TableParser(HTMLParser):
    """Collects the text of every table row as a list of cell strings."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_history_html(html: str) -> list[TrackingEvent]:
    """Parse the Status | Date | Time | Depot table into events, newest first.
    Dates are DD/MM/YYYY local (Australian) time; the page gives no time zone."""
    parser = _TableParser()
    parser.feed(html)
    events: list[tuple[datetime | None, TrackingEvent]] = []
    in_history = False
    for row in parser.rows:
        if [cell.lower() for cell in row] == _HISTORY_HEADER:
            in_history = True
            continue
        if not in_history or len(row) != 4 or not row[0]:
            continue
        description, day, time, depot = row
        try:
            when = datetime.strptime(f"{day} {time}", "%d/%m/%Y %H:%M:%S")
        except ValueError:
            when = None
        events.append(
            (
                when,
                TrackingEvent(
                    description=description,
                    location=depot or None,
                    occurred_at=when.isoformat() if when else None,
                ),
            )
        )
    events.sort(key=lambda pair: pair[0] or datetime.min, reverse=True)
    return [event for _, event in events]
