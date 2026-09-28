"""Load the input data files into Postgres.

    python -m app.seed

Reads DATA_DIR/sku_data.json (the SQL-like query site result) and
DATA_DIR/orders.json (orders, order_lines and tracking, mirroring the brief's
tables). Safe to re-run: everything is replaced in one transaction.

Validation policy:
- A bad order line (unknown SKU, invalid quantity, unknown tracking ref) is
  stored and flagged, so it can be shown to the user with the reason.
- A line whose order does not exist, or an order whose date cannot be read,
  cannot be stored meaningfully and is skipped with a warning.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import delete

from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import Order, OrderLine, Product, Shipment, ShippingQuote
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

log = logging.getLogger("seed")


def _read_json(path: Path) -> Any:
    # utf-8-sig: tolerate a byte-order mark (files saved from Windows tools often have one)
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _measure(parse, row: dict[str, Any], field: str, sku: str):
    try:
        return parse(row.get(field))
    except ParseError as exc:
        log.warning("Product %s: %s; stored as empty", sku, exc)
        return None


def build_products(rows: list[dict[str, Any]]) -> list[Product]:
    products: dict[str, Product] = {}
    for row in rows:
        sku = normalise_sku(row.get("SKU", ""))
        if not sku:
            log.warning("Skipping a product row without a SKU")
            continue
        if sku in products:
            log.warning("Duplicate product %s; keeping the first row", sku)
            continue
        products[sku] = Product(
            sku=sku,
            product_name=_text(row.get("ProductName")) or sku,
            barcode=_text(row.get("Barcode")),
            dosage_type=_text(row.get("DosageType")),
            product_type=_text(row.get("ProductType")),
            size=_text(row.get("Size")),
            status=_text(row.get("Status")),
            rrp=_measure(parse_money, row, "RRP", sku),
            length_mm=_measure(parse_length_mm, row, "length", sku),
            width_mm=_measure(parse_length_mm, row, "width", sku),
            height_mm=_measure(parse_length_mm, row, "height", sku),
            volume_mm3=_measure(parse_volume_mm3, row, "volume", sku),
            weight_g=_measure(parse_weight_g, row, "weight", sku),
            description=_text(row.get("Description")) if _text(row.get("Description")) != "." else None,
        )
    return list(products.values())


def build_orders(rows: list[dict[str, Any]]) -> list[Order]:
    orders: dict[str, Order] = {}
    for row in rows:
        order_no = _text(row.get("order_no"))
        if not order_no:
            log.warning("Skipping an order without an order number")
            continue
        if order_no in orders:
            log.warning("Duplicate order %s; keeping the first one", order_no)
            continue
        try:
            order_date = parse_order_date(row.get("order_date", ""))
        except ParseError as exc:
            log.warning("Skipping order %s: %s", order_no, exc)
            continue
        address_raw = _text(row.get("address")) or ""
        try:
            address = parse_au_address(address_raw)
        except ParseError as exc:
            log.warning("Order %s: %s; shipping quotes will be unavailable", order_no, exc)
            address = None
        orders[order_no] = Order(
            order_no=order_no,
            order_date=order_date,
            status=_text(row.get("status")) or "Unknown",
            company=_text(row.get("company")),
            customer_name=_text(row.get("customer_name")) or "Unknown",
            phone=_text(row.get("phone")),
            email=_text(row.get("email")),
            address_raw=address_raw,
            address_line=address.line if address else None,
            suburb=address.suburb if address else None,
            state=address.state if address else None,
            postcode=address.postcode if address else None,
        )
    return list(orders.values())


def build_shipments(rows: list[dict[str, Any]]) -> list[Shipment]:
    shipments: dict[str, Shipment] = {}
    for row in rows:
        ref = _text(row.get("assigned_tracking"))
        tracking_no = _text(row.get("tracking_no"))
        if not ref or not tracking_no:
            log.warning("Skipping a tracking row without a reference or number: %s", row)
            continue
        if ref in shipments:
            log.warning("Duplicate tracking reference %s; keeping the first one", ref)
            continue
        company = _text(row.get("logistics_company")) or "Unknown"
        shipments[ref] = Shipment(
            tracking_ref=ref,
            tracking_no=tracking_no,
            carrier=carrier_from_company(company),
            logistics_company=company,
        )
    return list(shipments.values())


def build_lines(
    rows: list[dict[str, Any]],
    orders: dict[str, Order],
    shipments: dict[str, Shipment],
    products: dict[str, Product],
) -> tuple[list[OrderLine], int]:
    lines: list[OrderLine] = []
    flagged = 0
    next_line_no: dict[str, int] = {}
    for row in rows:
        order_no = _text(row.get("order_no"))
        if order_no not in orders:
            log.warning("Skipping a line for unknown order %s: %s", order_no, row)
            continue
        sku = normalise_sku(row.get("sku", ""))
        raw_quantity = row.get("quantity")
        try:
            quantity = parse_quantity(raw_quantity)
        except ParseError as exc:
            log.warning("Order %s, SKU %s: %s", order_no, sku, exc)
            quantity = None
        ref = _text(row.get("assigned_tracking"))
        shipment = shipments.get(ref) if ref else None
        if ref and shipment is None:
            log.warning("Order %s, SKU %s: unknown tracking reference %s", order_no, sku, ref)
        if sku not in products:
            log.warning("Order %s: SKU %s is not in the product data", order_no, sku)
        if quantity is None or sku not in products or shipment is None:
            flagged += 1

        next_line_no[order_no] = next_line_no.get(order_no, 0) + 1
        line = OrderLine(
            line_no=next_line_no[order_no],
            sku=sku,
            quantity=quantity,
            quantity_raw=str(raw_quantity),
        )
        line.order = orders[order_no]
        line.shipment = shipment
        lines.append(line)
    return lines, flagged


async def seed(data_dir: Path) -> None:
    sku_file = data_dir / "sku_data.json"
    orders_file = data_dir / "orders.json"
    for path in (sku_file, orders_file):
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

    sku_data = _read_json(sku_file)
    order_data = _read_json(orders_file)
    product_rows = sku_data["rows"] if isinstance(sku_data, dict) else sku_data

    products = build_products(product_rows)
    orders = build_orders(order_data.get("orders", []))
    shipments = build_shipments(order_data.get("tracking", []))
    lines, flagged = build_lines(
        order_data.get("order_lines", []),
        {o.order_no: o for o in orders},
        {s.tracking_ref: s for s in shipments},
        {p.sku: p for p in products},
    )

    async with SessionLocal() as db, db.begin():
        # Replace everything; stored quotes may no longer match the new data.
        for model in (ShippingQuote, OrderLine, Order, Shipment, Product):
            await db.execute(delete(model))
        db.add_all([*products, *shipments, *orders, *lines])

    print(
        f"Seeded {len(products)} products, {len(orders)} orders, "
        f"{len(lines)} order lines ({flagged} flagged), {len(shipments)} shipments "
        f"from {data_dir}"
    )


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        await seed(Path(get_settings().data_dir))
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        log.error("Seeding failed: %s", exc)
        return 1
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    # psycopg's async mode cannot use Windows' default ProactorEventLoop.
    # Only matters for local runs on Windows; Docker runs on Linux.
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    sys.exit(asyncio.run(main(), loop_factory=loop_factory))
