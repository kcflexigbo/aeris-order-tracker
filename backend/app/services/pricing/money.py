from decimal import ROUND_HALF_UP, Decimal

GST_RATE = Decimal("0.10")
GST_DIVISOR = Decimal(1) + GST_RATE  # RRP includes GST: ex-GST = RRP / 1.10
CENT = Decimal("0.01")
UNIT_PRICE_PRECISION = Decimal("0.0001")
ZERO = Decimal("0.00")


def round_money(amount: Decimal) -> Decimal:
    """Round to cents, half-up (0.005 -> 0.01), as used for AUD invoices."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def round_unit_price(amount: Decimal) -> Decimal:
    """Ex-GST unit prices are shown to 4 decimals (149 / 1.10 = 135.4545) so that
    unit price x quantity visibly matches the line subtotal, which is rounded to cents."""
    return amount.quantize(UNIT_PRICE_PRECISION, rounding=ROUND_HALF_UP)


def ex_gst(amount_incl_gst: Decimal) -> Decimal:
    """Remove GST from a GST-inclusive amount. Not rounded; callers round at the point of display."""
    return amount_incl_gst / GST_DIVISOR


def gst_on(amount_ex_gst: Decimal) -> Decimal:
    return round_money(amount_ex_gst * GST_RATE)
