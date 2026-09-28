from decimal import Decimal

from app.services.shipping import PackItem, build_parcel

D = Decimal


def item(sku, qty, l, w, h, vol, g):
    return PackItem(sku, qty, D(l), D(w), D(h), D(vol) if vol else None, D(g) if g else None)


def test_order_2_tnt_carton():
    items = [
        item("HALGEO15", 1, 76, 76, 78, 450528, 68),
        item("MCMW10", 2, 76, 76, 79, 456304, 59),
        item("MCBO30", 3, 76, 76, 79, 456304, 59),
    ]
    parcel, warnings = build_parcel(items, D("1.25"), D("0.3"))
    assert (parcel.length_cm, parcel.width_cm, parcel.height_cm) == (16, 16, 16)
    assert parcel.weight_kg == D("0.67")  # 363 g + 0.3 kg, rounded up
    assert parcel.item_count == 6
    assert warnings == []


def test_volume_falls_back_to_dimensions_and_missing_data_warns():
    parcel, warnings = build_parcel(
        [item("A", 1, 100, 100, 100, None, 500), PackItem("B", 1, None, None, None, None, None)],
        D("1"),
        D("0"),
    )
    assert parcel.length_cm == 10
    assert parcel.weight_kg == D("0.50")
    assert len(warnings) == 2


def test_nothing_to_pack():
    assert build_parcel([], D("1.25"), D("0.3")) == (None, [])
