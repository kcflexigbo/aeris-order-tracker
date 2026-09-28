"""Shipment fee per order.

The fee is calculated at order level as the sum of one carrier quote per
(order, shipment). Orders are never combined, even if they share a carrier.
Quotes are stored in Postgres so the page does not call the carriers on every
view; `refresh=True` re-quotes. A failed quote is stored with fee 0.00 and the
reason, as the brief requires ("display A$0.00 and continue").

Flow: (1) work out which shipments need a quote and build their cartons,
(2) request all quotes concurrently, (3) write the results in one transaction.
The database session is only used before and after the concurrent step, because
an AsyncSession must not be shared between concurrent tasks.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    CARRIER_STARTRACK,
    CARRIER_TNT,
    QUOTE_NOT_IMPLEMENTED,
    QUOTE_OK,
    QUOTE_UNAVAILABLE,
    Order,
    OrderLine,
    Product,
    Shipment,
    ShippingQuote,
)
from app.services.couriers import Couriers, Parcel, Place, QuoteResult
from app.services.couriers.types import STATE_NOT_IMPLEMENTED, STATE_OK, STATE_UNAVAILABLE
from app.services.pricing import ZERO, round_money
from app.services.shipping.parcel import PackItem, build_parcel

_STATE_TO_QUOTE_STATUS = {STATE_OK: QUOTE_OK, STATE_NOT_IMPLEMENTED: QUOTE_NOT_IMPLEMENTED}


@dataclass(frozen=True)
class _Job:
    shipment: Shipment
    parcel: Parcel | None
    warnings: list[str]


async def quote_order(
    db: AsyncSession,
    order: Order,
    products: dict[str, Product],
    couriers: Couriers,
    settings: Settings,
    refresh: bool = False,
) -> list[ShippingQuote]:
    """`order` must be loaded with its lines and each line's shipment (selectinload)."""
    groups: dict[int, list[OrderLine]] = defaultdict(list)
    shipments: dict[int, Shipment] = {}
    for line in order.lines:
        if line.shipment is not None:
            groups[line.shipment.id].append(line)
            shipments[line.shipment.id] = line.shipment

    existing = {
        q.shipment_id: q
        for q in await db.scalars(select(ShippingQuote).where(ShippingQuote.order_no == order.order_no))
    }

    # 1. Plan: which shipments need a (new) quote, and what carton each one is
    jobs: list[_Job] = []
    for shipment_id, lines in groups.items():
        if shipment_id in existing and not refresh:
            continue
        items = [
            _pack_item(line, products[line.sku])
            for line in lines
            if line.quantity is not None and line.sku in products
        ]
        parcel, warnings = build_parcel(items, settings.packing_factor, settings.packaging_weight_kg)
        jobs.append(_Job(shipments[shipment_id], parcel, warnings))

    # 2. Ask the carriers, all at once
    origin = Place(settings.origin_suburb, settings.origin_state, settings.origin_postcode)
    results: list[QuoteResult] = await asyncio.gather(
        *(_quote_job(couriers, job, order, origin) for job in jobs)
    )

    # 3. Store every result, including failures (fee 0.00 + reason)
    now = datetime.now(UTC)
    for job, result in zip(jobs, results):
        quote = existing.get(job.shipment.id) or ShippingQuote(
            order_no=order.order_no, shipment_id=job.shipment.id
        )
        ok = result.state == STATE_OK
        quote.carrier = job.shipment.carrier
        quote.status = _STATE_TO_QUOTE_STATUS.get(result.state, QUOTE_UNAVAILABLE)
        quote.service_code = result.service_code
        quote.service_name = result.service_name
        quote.fee_ex_gst = round_money(result.fee_ex_gst) if ok and result.fee_ex_gst is not None else ZERO
        quote.fee_incl_gst = round_money(result.fee_incl_gst) if ok and result.fee_incl_gst is not None else ZERO
        quote.message = "; ".join(m for m in [result.message, *job.warnings] if m) or None
        quote.source = result.source
        quote.parcel = job.parcel.as_dict() if job.parcel else None
        quote.quoted_at = now
        db.add(quote)
        existing[job.shipment.id] = quote

    if jobs:
        await db.commit()
    return [existing[shipment_id] for shipment_id in groups]


def shipment_fee(quotes: list[ShippingQuote]) -> Decimal:
    """Order-level Shipment Fee (GST inclusive). Failed quotes contribute 0.00."""
    return round_money(sum((q.fee_incl_gst for q in quotes), ZERO))


async def _quote_job(couriers: Couriers, job: _Job, order: Order, origin: Place) -> QuoteResult:
    carrier = job.shipment.carrier
    if job.parcel is None:
        return QuoteResult(
            carrier=carrier, state=STATE_UNAVAILABLE, message="No valid items in this shipment to quote"
        )
    if not (order.suburb and order.state and order.postcode):
        return QuoteResult(
            carrier=carrier,
            state=STATE_UNAVAILABLE,
            message="The delivery address could not be read, so no quote was requested",
        )
    destination = Place(order.suburb, order.state, order.postcode)
    if carrier == CARRIER_STARTRACK:
        return await couriers.auspost.quote(job.parcel, origin, destination)
    if carrier == CARRIER_TNT:
        return await couriers.tnt.quote(job.parcel, origin, destination)
    return QuoteResult(
        carrier=carrier,
        state=STATE_NOT_IMPLEMENTED,
        message="No pricing integration for this logistics company",
    )


def _pack_item(line: OrderLine, product: Product) -> PackItem:
    return PackItem(
        sku=line.sku,
        quantity=line.quantity or 0,
        length_mm=product.length_mm,
        width_mm=product.width_mm,
        height_mm=product.height_mm,
        volume_mm3=product.volume_mm3,
        weight_g=product.weight_g,
    )
