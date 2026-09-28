from decimal import Decimal

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    """SKU master data, loaded from the SQL-like query site snapshot (data/sku_data.json).

    Measurements are stored as plain numbers in fixed units (mm, mm3, g);
    the source strings such as "76.0mm" are parsed during seeding.
    """

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(255))
    barcode: Mapped[str | None] = mapped_column(String(64))
    dosage_type: Mapped[str | None] = mapped_column(String(128))
    product_type: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    rrp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # AUD, GST inclusive
    length_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    width_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    height_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    volume_mm3: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    weight_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(Text)
