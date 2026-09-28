from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OrderLine(Base):
    """One SKU line of an order.

    `sku` deliberately has no foreign key to products: a line with an unknown
    SKU must still be stored so it can be shown as "SKU not found".
    `quantity` is NULL when the supplied value is not a whole number;
    `quantity_raw` keeps the original input for display.
    """

    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(ForeignKey("orders.order_no", ondelete="CASCADE"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    sku: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int | None] = mapped_column(Integer)
    quantity_raw: Mapped[str] = mapped_column(String(64))
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipments.id", ondelete="SET NULL"))

    order: Mapped["Order"] = relationship(back_populates="lines", lazy="raise")  # noqa: F821
    shipment: Mapped["Shipment | None"] = relationship(lazy="raise")  # noqa: F821
