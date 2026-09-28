from datetime import date, datetime

from app.parsing.errors import ParseError

# Australian day-first formats only. A US-style parser would read 03/12/25 as 12 March.
_FORMATS = ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d")


def parse_order_date(value: str) -> date:
    text = str(value).strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ParseError(f"order date must be DD/MM/YY, got {value!r}")
