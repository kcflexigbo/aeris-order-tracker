from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Order(Base):
    """Order header. The address is kept as supplied and also split into parts,
    because the suburb and postcode are needed for carrier quotes.

    Relationships use lazy="raise": with async SQLAlchemy an implicit lazy load
    cannot run, so queries must load what they need explicitly (selectinload),
    and forgetting to do so fails loudly instead of intermittently."""

    __tablename__ = "orders"

    order_no: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(64))
    company: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    address_raw: Mapped[str] = mapped_column(String(512))
    address_line: Mapped[str | None] = mapped_column(String(255))
    suburb: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(8))
    postcode: Mapped[str | None] = mapped_column(String(8))

    lines: Mapped[list["OrderLine"]] = relationship(  # noqa: F821
        back_populates="order", order_by="OrderLine.line_no", cascade="all, delete-orphan", lazy="raise"
    )
