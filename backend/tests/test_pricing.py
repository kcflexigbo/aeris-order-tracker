from decimal import Decimal

from app.services.pricing import LineInput, price_line, price_lines, summarise

D = Decimal


def line(n, sku, qty, rrp, found=True):
    return LineInput(n, sku, qty, str(qty), found, D(rrp) if rrp is not None else None)


ORDER_1 = [
    line(1, "TBAMET10", 3, "99.00"),
    line(2, "TBAMET28", 1, "199.00"),
    line(3, "TBOPAL28", 1, "199.00"),
    line(4, "HARNIG", 4, "149.00"),
    line(5, "LELCBD100", 6, "140.00"),
]
ORDER_2 = [
    line(1, "AURPUR10", 10, "99.00"),
    line(2, "HALGEO15", 1, "110.00"),
    line(3, "MCMW10", 2, "129.00"),
    line(4, "MCBO30", 3, "99.00"),
]


def test_order_1_totals():
    t = summarise(price_lines(ORDER_1))
    assert (t.subtotal, t.gst, t.total) == (D("1937.28"), D("193.73"), D("2131.01"))


def test_order_2_totals_with_shipping():
    t = summarise(price_lines(ORDER_2), shipment_fee=D("36.27"))
    assert (t.subtotal, t.gst, t.shipment_fee, t.total) == (D("1504.55"), D("150.46"), D("36.27"), D("1691.28"))


def test_unit_price_shown_to_4dp_matches_line_subtotal():
    p = price_line(line(4, "HARNIG", 4, "149.00"))
    assert p.ex_gst_unit_price == D("135.4545")
    assert p.line_subtotal == D("541.82")  # 149 x 4 / 1.10 = 541.818...


def test_lines_add_up_to_subtotal():
    priced = price_lines(ORDER_1)
    assert sum(p.line_subtotal for p in priced) == summarise(priced).subtotal


def test_bad_lines_are_excluded_with_reason():
    priced = price_lines(
        [
            line(1, "MCBO30", 2, "99.00"),
            line(2, "NOTASKU99", 1, None, found=False),
            LineInput(3, "TBAMET10", None, "0", True, D("99.00")),
            line(4, "NOPRICE", 1, None),
        ]
    )
    assert [p.status for p in priced] == ["ok", "sku_not_found", "invalid_quantity", "missing_price"]
    assert all(p.message for p in priced[1:])
    assert priced[2].ex_gst_unit_price == D("90.0000")  # still shown for the invalid-quantity line
    t = summarise(priced)
    assert (t.subtotal, t.gst, t.excluded_lines) == (D("180.00"), D("18.00"), 2 + 1)


def test_gst_rounds_half_up():
    t = summarise([price_line(line(1, "X", 1, "0.55"))])  # 0.50 ex GST -> GST 0.05
    assert (t.subtotal, t.gst) == (D("0.50"), D("0.05"))
