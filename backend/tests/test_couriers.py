"""Courier clients against canned responses (httpx.MockTransport); no network."""

import asyncio
import json
from decimal import Decimal
from urllib.parse import parse_qs, unquote

import httpx

from app.config import Settings
from app.services.couriers import AusPostClient, Parcel, Place, TntClient

SETTINGS = Settings(
    _env_file=None,
    auspost_base_url="https://auspost.test/test/shipping/v1",
    auspost_api_key="key",
    auspost_password="secret",
    auspost_account_number_startrack="12345678",
    tnt_tracking_url="https://tnt.test/CnmHxAS.asp",
    tnt_rtt_url="https://uat.tnt.test/rtt",
    tnt_uat_username="user",
    tnt_uat_password="pw",
    tnt_uat_account="30000000",
)
PARCEL = Parcel(16, 16, 16, Decimal("0.67"), 6)
ORIGIN = Place("GLADESVILLE", "NSW", "2111")
DEST = Place("FITZROY", "VIC", "3065")

ST_OK = {
    "tracking_results": [
        {
            "tracking_id": "2FWZ50008569",
            "consignment": {
                "status": "Delivered in Full",
                "events": [{"location": "LAKE CARGELLIGO NSW", "description": "Delivered", "date": "2025-02-13T11:49:59+11:00"}],
            },
            "trackable_items": [
                {
                    "events": [
                        {"location": "LAKE CARGELLIGO NSW", "description": "Delivered", "date": "2025-02-13T11:49:59+11:00"},
                        {"location": "TULLAMARINE VIC", "description": "Processed", "date": "2025-02-11T22:14:41+11:00"},
                    ]
                }
            ],
        },
        {"tracking_id": "BAD1", "errors": [{"code": "ESB-10001", "name": "Invalid tracking ID"}]},
    ]
}

TNT_HTML = """<table><tr><td>Status</td><td>Date</td><td>Time</td><td>Depot</td></tr>
<tr><td><font>We&apos;ve collected your shipment</font></td><td>03/12/2025</td><td>15:27:46</td><td>Sydney - Enfield</td></tr>
<tr><td><font>We&apos;ve delivered your shipment </font></td><td>04/12/2025</td><td>13:00:41</td><td>Melbourne - Airport</td></tr>
</table>"""

RTT_OK = """<?xml version="1.0"?><response xmlns="http://www.tntexpress.com.au"><ratedTransitTimeResponse><ratedProducts>
<ratedProduct><product><code>75</code><description>Overnight Express</description></product><quote currency="AUD"><price>15.42</price></quote></ratedProduct>
<ratedProduct><product><code>76</code><description>Road Express</description></product><quote currency="AUD"><price>18.18</price></quote></ratedProduct>
</ratedProducts></ratedTransitTimeResponse></response>"""


def run(coro):
    return asyncio.run(coro)


def client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_auspost_tracking_merges_events_and_maps_per_id_errors():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        return httpx.Response(200, json=ST_OK)

    async def go():
        async with client(handler) as http:
            return await AusPostClient(SETTINGS, http).track(["2FWZ50008569", "BAD1"])

    results = run(go())
    ok, bad = results["2FWZ50008569"], results["BAD1"]
    assert ok.state == "ok" and ok.status == "Delivered in Full"
    assert [e.description for e in ok.events] == ["Delivered", "Processed"]  # de-duplicated, newest first
    assert ok.source == "Australia Post testbed (simulated data)"
    assert bad.state == "not_found" and bad.error_code == "ESB-10001"
    assert seen["headers"]["Account-Number"] == "12345678"
    assert seen["headers"]["Authorization"].startswith("Basic ")


def test_auspost_rejected_batch_is_retried_one_by_one():
    def handler(request: httpx.Request) -> httpx.Response:
        ids = request.url.params["tracking_ids"].split(",")
        if len(ids) > 1:
            return httpx.Response(400, json={"errors": [{"code": "51103", "name": "MIXED", "message": "mixed ids"}]})
        if ids == ["2FWZ50008569"]:
            return httpx.Response(200, json={"tracking_results": [ST_OK["tracking_results"][0]]})
        return httpx.Response(400, json={"errors": [{"code": "51103", "message": "bad id"}]})

    async def go():
        async with client(handler) as http:
            return await AusPostClient(SETTINGS, http).track(["2FWZ50008569", "XXXX1"])

    results = run(go())
    assert results["2FWZ50008569"].state == "ok"
    assert results["XXXX1"].state == "not_found"


def test_auspost_auth_failure_is_unavailable_not_an_exception():
    body = {"errors": [{"message": "The request failed authentication", "error_code": "API_001"}]}

    async def go():
        async with client(lambda r: httpx.Response(401, json=body)) as http:
            return await AusPostClient(SETTINGS, http).track(["2FWZ50008569"])

    r = run(go())["2FWZ50008569"]
    assert r.state == "unavailable" and r.error_code == "API_001" and "401" in r.message


def test_network_error_is_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    async def go():
        async with client(handler) as http:
            return await AusPostClient(SETTINGS, http).track(["2FWZ50008569"]), await TntClient(SETTINGS, http).track("305506914")

    st, tnt = run(go())
    assert st["2FWZ50008569"].state == "unavailable"
    assert tnt.state == "unavailable"


def test_auspost_quote():
    summary = {"shipments": [{"shipment_summary": {"total_cost": 16.27, "total_cost_ex_gst": 14.79}}]}

    async def go():
        async with client(lambda r: httpx.Response(200, json=summary)) as http:
            return await AusPostClient(SETTINGS, http).quote(PARCEL, ORIGIN, DEST)

    q = run(go())
    assert (q.state, q.fee_ex_gst, q.fee_incl_gst, q.service_name) == ("ok", Decimal("14.79"), Decimal("16.27"), "StarTrack Express")


def test_tnt_history_parsed_newest_first():
    async def go():
        async with client(lambda r: httpx.Response(200, text=TNT_HTML)) as http:
            return await TntClient(SETTINGS, http).track("305506914")

    r = run(go())
    assert r.state == "ok"
    assert r.status == "We've delivered your shipment"
    assert r.last_update == "2025-12-04T13:00:41"
    assert r.last_location == "Melbourne - Airport"
    assert len(r.events) == 2


def test_tnt_invalid_connote_is_rejected_without_a_request():
    def handler(request):
        raise AssertionError("no request expected")

    async def go():
        async with client(handler) as http:
            return await TntClient(SETTINGS, http).track("BAD#CONNOTE")

    r = run(go())
    assert r.state == "not_found" and r.error_code == "INVALID_CONNOTE"


def test_tnt_rtt_quote_double_encodes_and_adds_gst():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        captured["xml"] = form["XMLRequest"][0]
        return httpx.Response(200, text=RTT_OK)

    async def go():
        async with client(handler) as http:
            return await TntClient(SETTINGS, http).quote(PARCEL, ORIGIN, DEST)

    q = run(go())
    assert captured["xml"].startswith("%3C%3Fxml")  # still URL-encoded after form decoding
    xml = unquote(captured["xml"])
    assert "<postCode>2111</postCode>" in xml and "<senderAccount>30000000</senderAccount>" in xml
    assert (q.service_code, q.fee_ex_gst, q.fee_incl_gst) == ("76", Decimal("18.18"), Decimal("20.00"))


def test_tnt_rtt_broken_rule_is_unavailable_with_reason():
    xml = """<response xmlns="http://www.tntexpress.com.au"><ratedTransitTimeResponse><brokenRules><brokenRule>
    <code>590</code><description>The Sender/Collection Suburb and Postcode (RYDE/2111) are invalid.</description>
    </brokenRule></brokenRules></ratedTransitTimeResponse></response>"""

    async def go():
        async with client(lambda r: httpx.Response(200, text=xml)) as http:
            return await TntClient(SETTINGS, http).quote(PARCEL, Place("RYDE", "NSW", "2111"), DEST)

    q = run(go())
    assert q.state == "unavailable" and "590" in q.message and q.fee_incl_gst is None
