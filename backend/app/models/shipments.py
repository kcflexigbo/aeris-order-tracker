from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Carrier codes derived from the "Logistics Company" column
CARRIER_STARTRACK = "STARTRACK"
CARRIER_TNT = "TNT"
CARRIER_UNKNOWN = "UNKNOWN"


class Shipment(Base):
    """A tracked consignment ("Track 1" -> tracking number -> carrier)."""

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_ref: Mapped[str] = mapped_column(String(64), unique=True)
    tracking_no: Mapped[str] = mapped_column(String(64))
    carrier: Mapped[str] = mapped_column(String(16))
    logistics_company: Mapped[str] = mapped_column(String(128))
