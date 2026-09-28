from decimal import Decimal, InvalidOperation

from app.parsing.errors import ParseError


def parse_quantity(value: object) -> int:
    """Quantity must be a positive whole number. Accepts 3, "3", 3.0; rejects "two", 0, -1, 1.5."""
    if isinstance(value, bool):
        raise ParseError(f"quantity must be a positive whole number, got {value!r}")
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ParseError(f"quantity must be a positive whole number, got {value!r}") from exc
    if not number.is_finite() or number != number.to_integral_value() or number <= 0:
        raise ParseError(f"quantity must be a positive whole number, got {value!r}")
    return int(number)
