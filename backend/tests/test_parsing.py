from datetime import date
from decimal import Decimal

import pytest

from app.parsing import (
    ParseError,
    carrier_from_company,
    normalise_sku,
    parse_au_address,
    parse_length_mm,
    parse_money,
    parse_order_date,
    parse_quantity,
    parse_volume_mm3,
    parse_weight_g,
)


def test_dates_are_day_first():
    assert parse_order_date("03/12/25") == date(2025, 12, 3)
    assert parse_order_date("30/11/25") == date(2025, 11, 30)
    with pytest.raises(ParseError):
        parse_order_date("12/31/25")  # US order is rejected, not silently swapped


def test_address_split():
    a = parse_au_address("125 Toorak Road, South Yarra VIC 3141")
    assert (a.line, a.suburb, a.state, a.postcode) == ("125 Toorak Road", "SOUTH YARRA", "VIC", "3141")
    with pytest.raises(ParseError):
        parse_au_address("125 Toorak Road South Yarra")


def test_measures_with_units():
    assert parse_length_mm("76.0mm") == Decimal("76.0")
    assert parse_length_mm("7.6cm") == Decimal("76.0")
    assert parse_weight_g("0.02kg") == Decimal("20.00")
    assert parse_volume_mm3("450528.0mm³") == Decimal("450528.0")
    assert parse_length_mm("") is None
    with pytest.raises(ParseError):
        parse_weight_g("heavy")


def test_money():
    assert parse_money("110.00") == Decimal("110.00")
    assert parse_money("$1,234.50") == Decimal("1234.50")
    with pytest.raises(ParseError):
        parse_money("-1")


@pytest.mark.parametrize("value, expected", [(3, 3), ("3", 3), (3.0, 3), (" 10 ", 10)])
def test_valid_quantities(value, expected):
    assert parse_quantity(value) == expected


@pytest.mark.parametrize("value", [0, -1, 1.5, "two", "", None, True])
def test_invalid_quantities(value):
    with pytest.raises(ParseError):
        parse_quantity(value)


def test_sku_and_carrier_normalisation():
    assert normalise_sku(" tbamet10 ") == "TBAMET10"
    assert carrier_from_company("StarTrack/Auspost") == "STARTRACK"
    assert carrier_from_company("TNT") == "TNT"
    assert carrier_from_company("DHL") == "UNKNOWN"
