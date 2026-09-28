"""Assembles API views of orders: pricing + stored/fresh shipping quotes + totals."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.models import Order, OrderLine, Product, Shipment, ShippingQuote
from app.schemas import (
    AddressOut,
    OrderDetail,
    OrderLineOut,
    OrderSummary,
    ShipmentOut,
    ShippingQuoteOut,
    TotalsOut,
)
from app.services.couriers import Couriers
from app.services.pricing import LINE_OK, LineInput, PricedLine, price_lines, summarise
from app.services.shipping import quote_order, shipment_fee

_ORDER_LOAD = selectinload(Order.lines).selectinload(OrderLine.shipment)


async def load_products(db: AsyncSession) -> dict[str, Product]:
    return {p.sku: p for p in await db.scalars(select(Product))}


async def load_order(db: AsyncSession, order_no: str) -> Order | None:
    return await db.scalar(select(Order).where(Order.order_no == order_no).options(_ORDER_LOAD))


def price_order(order: Order, products: dict[str, Product]) -> list[PricedLine]:
    return price_lines(
        [
            LineInput(
                line_no=line.line_no,
                sku=line.sku,
                quantity=line.quantity,
                quantity_raw=line.quantity_raw,
                product_found=line.sku in products,
                rrp=products[line.sku].rrp if line.sku in products else None,
            )
            for line in order.lines
        ]
    )


def order_shipments(order: Order) -> list[Shipment]:
    """Distinct shipments of an order, in line order."""
    seen: dict[int, Shipment] = {}
    for line in order.lines:
        if line.shipment is not None and line.shipment.id not in seen:
            seen[line.shipment.id] = line.shipment
    return list(seen.values())


async def list_orders(db: AsyncSession) -> list[OrderSummary]:
    products = await load_products(db)
    orders = await db.scalars(select(Order).options(_ORDER_LOAD).order_by(Order.order_date, Order.order_no))
    summaries = []
    for order in orders:
        priced = price_order(order, products)
        summaries.append(
            OrderSummary(
                order_no=order.order_no,
                order_date=order.order_date,
                status=order.status,
                company=order.company,
                customer_name=order.customer_name,
                destination=_destination(order),
                line_count=len(order.lines),
                flagged_lines=sum(1 for p in priced if p.status != LINE_OK),
                shipment_count=len(order_shipments(order)),
            )
        )
    return summaries


async def build_order_detail(
    db: AsyncSession,
    order: Order,
    couriers: Couriers,
    settings: Settings,
    refresh_quotes: bool = False,
) -> OrderDetail:
    products = await load_products(db)
    quotes = await quote_order(db, order, products, couriers, settings, refresh=refresh_quotes)
    quotes_by_shipment = {q.shipment_id: q for q in quotes}
    priced = price_order(order, products)
    totals = summarise(priced, shipment_fee(quotes))

    lines_by_no = {line.line_no: line for line in order.lines}
    lines_out = []
    for p in priced:
        line = lines_by_no[p.line_no]
        product = products.get(line.sku)
        shipment = line.shipment
        lines_out.append(
            OrderLineOut(
                line_no=p.line_no,
                image_label=f"Product {p.line_no}",
                sku=p.sku,
                product_name=product.product_name if product else None,
                description=product.description if product else None,
                dosage_type=product.dosage_type if product else None,
                quantity=p.quantity,
                quantity_raw=p.quantity_raw,
                rrp=p.rrp,
                ex_gst_unit_price=p.ex_gst_unit_price,
                line_subtotal=p.line_subtotal,
                status=p.status,
                message=p.message,
                tracking_ref=shipment.tracking_ref if shipment else None,
                tracking_no=shipment.tracking_no if shipment else None,
                carrier=shipment.carrier if shipment else None,
            )
        )

    shipments_out = [
        ShipmentOut(
            id=s.id,
            tracking_ref=s.tracking_ref,
            tracking_no=s.tracking_no,
            carrier=s.carrier,
            logistics_company=s.logistics_company,
            line_count=sum(1 for line in order.lines if line.shipment_id == s.id),
            quote=_quote_out(quotes_by_shipment.get(s.id)),
        )
        for s in order_shipments(order)
    ]

    warnings = []
    if totals.excluded_lines:
        n = totals.excluded_lines
        warnings.append(f"{n} line{'s are' if n > 1 else ' is'} excluded from the totals")
    unassigned = sum(1 for line in order.lines if line.shipment is None)
    if unassigned:
        warnings.append(f"{unassigned} line(s) have no known tracking reference and are not included in any shipment")
    if not order.postcode:
        warnings.append("The delivery address could not be read; shipping quotes are unavailable")

    return OrderDetail(
        order_no=order.order_no,
        order_date=order.order_date,
        status=order.status,
        company=order.company,
        customer_name=order.customer_name,
        phone=order.phone,
        email=order.email,
        address=AddressOut(
            raw=order.address_raw,
            line=order.address_line,
            suburb=order.suburb,
            state=order.state,
            postcode=order.postcode,
        ),
        lines=lines_out,
        shipments=shipments_out,
        totals=TotalsOut(
            subtotal=totals.subtotal,
            gst=totals.gst,
            shipment_fee=totals.shipment_fee,
            total=totals.total,
            excluded_lines=totals.excluded_lines,
        ),
        warnings=warnings,
    )


def _destination(order: Order) -> str | None:
    if order.suburb and order.state and order.postcode:
        return f"{order.suburb} {order.state} {order.postcode}"
    return None


def _quote_out(quote: ShippingQuote | None) -> ShippingQuoteOut | None:
    if quote is None:
        return None
    return ShippingQuoteOut(
        status=quote.status,
        service_code=quote.service_code,
        service_name=quote.service_name,
        fee_ex_gst=quote.fee_ex_gst,
        fee_incl_gst=quote.fee_incl_gst,
        message=quote.message,
        source=quote.source,
        parcel=quote.parcel,
        quoted_at=quote.quoted_at,
    )
