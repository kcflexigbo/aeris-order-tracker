import re
from dataclasses import dataclass

from app.parsing.errors import ParseError

AU_STATES = ("NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT")

# "<street>, <suburb> <STATE> <postcode>", e.g. "125 Toorak Road, South Yarra VIC 3141"
_ADDRESS_RE = re.compile(
    r"^\s*(?P<line>.+?)\s*,\s*(?P<suburb>[A-Za-z][A-Za-z' .-]*?)\s+"
    rf"(?P<state>{'|'.join(AU_STATES)})\s+(?P<postcode>\d{{4}})\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AuAddress:
    line: str
    suburb: str
    state: str
    postcode: str


def parse_au_address(value: str) -> AuAddress:
    match = _ADDRESS_RE.match(str(value))
    if not match:
        raise ParseError(
            f"address must look like '<street>, <suburb> <STATE> <postcode>', got {value!r}"
        )
    return AuAddress(
        line=match["line"].strip(),
        suburb=" ".join(match["suburb"].split()).upper(),
        state=match["state"].upper(),
        postcode=match["postcode"],
    )
