"""Carton model for shipment-fee quotes.

Assumption (documented in the README): all valid lines of one order that travel
under the same tracking number are packed into ONE carton.
    carton volume = sum(item volume x quantity) x packing factor (default 1.25, for void fill)
    carton shape  = a cube with that volume, sides rounded up to whole cm
    carton weight = sum(item weight x quantity) + packaging weight (default 0.3 kg)
Item volume uses the `volume` column, or length x width x height when it is missing.
The sheet's Volumetric_GrossWeight column is ignored: it does not match the dimensions.
"""

import math
from dataclasses import dataclass
from decimal import ROUND_UP, Decimal

from app.services.couriers.types import Parcel

_KG = Decimal("0.01")


@dataclass(frozen=True)
class PackItem:
    sku: str
    quantity: int
    length_mm: Decimal | None
    width_mm: Decimal | None
    height_mm: Decimal | None
    volume_mm3: Decimal | None
    weight_g: Decimal | None


def item_volume_mm3(item: PackItem) -> Decimal | None:
    if item.volume_mm3:
        return item.volume_mm3
    if item.length_mm and item.width_mm and item.height_mm:
        return item.length_mm * item.width_mm * item.height_mm
    return None


def build_parcel(
    items: list[PackItem], packing_factor: Decimal, packaging_weight_kg: Decimal
) -> tuple[Parcel | None, list[str]]:
    """Returns the carton (None when there is nothing to pack) and any warnings."""
    warnings: list[str] = []
    total_volume = Decimal(0)
    total_weight_g = Decimal(0)
    unit_count = 0

    for item in items:
        volume = item_volume_mm3(item)
        if volume is None:
            warnings.append(f"{item.sku} has no dimensions and was left out of the carton size")
        else:
            total_volume += volume * item.quantity
        if item.weight_g is None:
            warnings.append(f"{item.sku} has no weight and was left out of the carton weight")
        else:
            total_weight_g += item.weight_g * item.quantity
        unit_count += item.quantity

    if unit_count == 0:
        return None, warnings

    carton_mm3 = total_volume * packing_factor
    side_cm = max(1, math.ceil(float(carton_mm3) ** (1 / 3) / 10))
    weight_kg = (total_weight_g / 1000 + packaging_weight_kg).quantize(_KG, rounding=ROUND_UP)
    return (
        Parcel(
            length_cm=side_cm,
            width_cm=side_cm,
            height_cm=side_cm,
            weight_kg=max(weight_kg, _KG),
            item_count=unit_count,
        ),
        warnings,
    )
