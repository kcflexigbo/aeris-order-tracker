"""Order pricing.

Rules (from the assessment brief):
    Ex-GST unit price   = RRP / 1.10
    Line subtotal       = ex-GST unit price x quantity
    Order subtotal      = sum of line subtotals (ex GST)
    GST                 = order subtotal x 10%
    Order total         = subtotal + GST + shipment fee

Rounding: each line subtotal is computed from the unrounded ex-GST price
(RRP x qty / 1.10) and then rounded to cents, so the lines shown on screen add
up exactly to the subtotal. The ex-GST unit price is shown to 4 decimals
(e.g. 149 / 1.10 = 135.4545) so unit price x quantity visibly matches the line
subtotal (135.4545 x 4 = 541.818 -> 541.82). The order total can differ from
the RRP sum by a cent because each line is rounded.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.services.pricing.money import ZERO, ex_gst, gst_on, round_money, round_unit_price

LINE_OK = "ok"
LINE_SKU_NOT_FOUND = "sku_not_found"
LINE_INVALID_QUANTITY = "invalid_quantity"
LINE_MISSING_PRICE = "missing_price"


@dataclass(frozen=True)
class LineInput:
    line_no: int
    sku: str
    quantity: int | None  # None when the supplied quantity was invalid
    quantity_raw: str
    product_found: bool
    rrp: Decimal | None  # GST inclusive


@dataclass(frozen=True)
class PricedLine:
    line_no: int
    sku: str
    quantity: int | None
    quantity_raw: str
    status: str
    message: str | None
    rrp: Decimal | None
    ex_gst_unit_price: Decimal | None
    line_subtotal: Decimal | None  # ex GST; None when the line is excluded from totals


@dataclass(frozen=True)
class OrderTotals:
    subtotal: Decimal  # ex GST
    gst: Decimal
    shipment_fee: Decimal
    total: Decimal
    excluded_lines: int


def price_line(line: LineInput) -> PricedLine:
    def excluded(status: str, message: str) -> PricedLine:
        return PricedLine(
            line_no=line.line_no,
            sku=line.sku,
            quantity=line.quantity,
            quantity_raw=line.quantity_raw,
            status=status,
            message=message,
            rrp=line.rrp,
            ex_gst_unit_price=round_unit_price(ex_gst(line.rrp)) if line.rrp is not None else None,
            line_subtotal=None,
        )

    if not line.product_found:
        return excluded(LINE_SKU_NOT_FOUND, f"SKU {line.sku} was not found in the product data")
    if line.rrp is None:
        return excluded(LINE_MISSING_PRICE, f"SKU {line.sku} has no RRP in the product data")
    if line.quantity is None:
        return excluded(
            LINE_INVALID_QUANTITY,
            f"quantity must be a positive whole number, got {line.quantity_raw!r}",
        )

    return PricedLine(
        line_no=line.line_no,
        sku=line.sku,
        quantity=line.quantity,
        quantity_raw=line.quantity_raw,
        status=LINE_OK,
        message=None,
        rrp=line.rrp,
        ex_gst_unit_price=round_unit_price(ex_gst(line.rrp)),
        line_subtotal=round_money(ex_gst(line.rrp * line.quantity)),
    )


def price_lines(lines: list[LineInput]) -> list[PricedLine]:
    return [price_line(line) for line in lines]


def summarise(lines: list[PricedLine], shipment_fee: Decimal = ZERO) -> OrderTotals:
    """Totals for one order. Lines that are not "ok" are excluded and counted."""
    subtotal = sum((l.line_subtotal for l in lines if l.line_subtotal is not None), ZERO)
    subtotal = round_money(subtotal)
    gst = gst_on(subtotal)
    shipment_fee = round_money(shipment_fee)
    return OrderTotals(
        subtotal=subtotal,
        gst=gst,
        shipment_fee=shipment_fee,
        total=subtotal + gst + shipment_fee,
        excluded_lines=sum(1 for l in lines if l.line_subtotal is None),
    )
