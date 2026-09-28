from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

QUOTE_OK = "ok"
QUOTE_UNAVAILABLE = "unavailable"
QUOTE_NOT_IMPLEMENTED = "not_implemented"


class ShippingQuote(Base):
    """Carrier quote for the part of one order that travels in one shipment.

    Keyed by (order, shipment) so orders for different recipients are never
    combined. The order's Shipment Fee is the sum of its quotes.
    A failed quote is stored with fee 0.00 and the reason in `message`.
    """

    __tablename__ = "shipping_quotes"
    __table_args__ = (UniqueConstraint("order_no", "shipment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(ForeignKey("orders.order_no", ondelete="CASCADE"), index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    carrier: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32))
    service_code: Mapped[str | None] = mapped_column(String(32))
    service_name: Mapped[str | None] = mapped_column(String(128))
    fee_ex_gst: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fee_incl_gst: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    message: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(128))  # e.g. "TNT RTT (UAT test rates)"
    parcel: Mapped[dict | None] = mapped_column(JSON)  # carton dimensions/weight sent to the carrier
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
