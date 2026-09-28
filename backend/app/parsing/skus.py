from app.models import CARRIER_STARTRACK, CARRIER_TNT, CARRIER_UNKNOWN


def normalise_sku(value: object) -> str:
    """ " tbamet10 " -> "TBAMET10", so lookups ignore case and stray whitespace."""
    return str(value).strip().upper()


def carrier_from_company(logistics_company: str) -> str:
    """Map the free-text "Logistics Company" column to a carrier code."""
    name = logistics_company.lower()
    if "startrack" in name or "auspost" in name or "australia post" in name:
        return CARRIER_STARTRACK
    if "tnt" in name:
        return CARRIER_TNT
    return CARRIER_UNKNOWN
