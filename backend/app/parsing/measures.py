import re
from decimal import Decimal, InvalidOperation

from app.parsing.errors import ParseError

# The SKU data returns measurements as text with units, e.g. "76.0mm", "68.0g",
# "0.02kg", "450528.0mm³". Everything is converted to mm, mm3 and g.
_MEASURE_RE = re.compile(r"^\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z³3]*)\s*$")

_LENGTH_TO_MM = {"": Decimal(1), "mm": Decimal(1), "cm": Decimal(10), "m": Decimal(1000)}
_MASS_TO_G = {"": Decimal(1), "g": Decimal(1), "kg": Decimal(1000)}
_VOLUME_TO_MM3 = {
    "": Decimal(1),
    "mm³": Decimal(1),
    "mm3": Decimal(1),
    "cm³": Decimal(1000),
    "cm3": Decimal(1000),
}


def _parse(value: object, units: dict[str, Decimal], kind: str) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    match = _MEASURE_RE.match(str(value))
    if not match:
        raise ParseError(f"{kind} {value!r} is not a number with a unit")
    unit = match["unit"].lower()
    if unit not in units:
        raise ParseError(f"{kind} {value!r} has an unsupported unit {match['unit']!r}")
    return Decimal(match["number"]) * units[unit]


def parse_length_mm(value: object) -> Decimal | None:
    return _parse(value, _LENGTH_TO_MM, "length")


def parse_weight_g(value: object) -> Decimal | None:
    return _parse(value, _MASS_TO_G, "weight")


def parse_volume_mm3(value: object) -> Decimal | None:
    return _parse(value, _VOLUME_TO_MM3, "volume")


def parse_money(value: object) -> Decimal | None:
    """ "110.00" -> Decimal("110.00"). Blank means no price."""
    if value is None or str(value).strip() == "":
        return None
    try:
        amount = Decimal(str(value).strip().lstrip("$").replace(",", ""))
    except InvalidOperation as exc:
        raise ParseError(f"price {value!r} is not a number") from exc
    if amount < 0:
        raise ParseError(f"price {value!r} is negative")
    return amount
