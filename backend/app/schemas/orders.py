"""Order API response models.

Money fields are Decimal; Pydantic serialises Decimal to a JSON *string*
("1937.28"), so the frontend never does floating-point money maths.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

LineStatus = Literal["ok", "sku_not_found", "invalid_quantity", "missing_price"]
QuoteStatus = Literal["ok", "unavailable", "not_implemented"]
Carrier = Literal["STARTRACK", "TNT", "UNKNOWN"]


class AddressOut(BaseModel):
    raw: str
    line: str | None
    suburb: str | None
    state: str | None
    postcode: str | None


class OrderSummary(BaseModel):
    order_no: str
    order_date: date
    status: str
    company: str | None
    customer_name: str
    destination: str | None  # "SOUTH YARRA VIC 3141"
    line_count: int
    flagged_lines: int  # lines excluded from totals (unknown SKU, invalid quantity, ...)
    shipment_count: int


class OrderLineOut(BaseModel):
    line_no: int
    image_label: str  # placeholder image text: "Product 1", "Product 2", ...
    sku: str
    product_name: str | None  # None when the SKU is not in the product data
    description: str | None
    dosage_type: str | None
    quantity: int | None  # None when the supplied quantity is invalid
    quantity_raw: str
    rrp: Decimal | None  # GST inclusive
    ex_gst_unit_price: Decimal | None  # 4 decimal places
    line_subtotal: Decimal | None  # ex GST, 2 dp; None when excluded from totals
    status: LineStatus
    message: str | None
    tracking_ref: str | None
    tracking_no: str | None
    carrier: Carrier | None


class ShippingQuoteOut(BaseModel):
    status: QuoteStatus
    service_code: str | None
    service_name: str | None
    fee_ex_gst: Decimal
    fee_incl_gst: Decimal  # this is what counts towards the Shipment Fee
    message: str | None
    source: str | None
    parcel: dict[str, Any] | None  # {"length_cm", "width_cm", "height_cm", "weight_kg", "item_count"}
    quoted_at: datetime


class ShipmentOut(BaseModel):
    id: int
    tracking_ref: str
    tracking_no: str
    carrier: Carrier
    logistics_company: str
    line_count: int
    quote: ShippingQuoteOut | None


class TotalsOut(BaseModel):
    currency: Literal["AUD"] = "AUD"
    subtotal: Decimal  # ex GST
    gst: Decimal  # 10% of subtotal
    shipment_fee: Decimal  # sum of shipment quotes, GST inclusive
    total: Decimal  # subtotal + gst + shipment_fee
    excluded_lines: int


class OrderDetail(BaseModel):
    order_no: str
    order_date: date
    status: str
    company: str | None
    customer_name: str
    phone: str | None
    email: str | None
    address: AddressOut
    lines: list[OrderLineOut]
    shipments: list[ShipmentOut]
    totals: TotalsOut
    warnings: list[str]  # order-level notes, e.g. "2 lines excluded from totals"
