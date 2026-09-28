"""Initial schema: products, orders, shipments, order_lines, shipping_quotes

Revision ID: 0001
Revises:
Create Date: 2026-09-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("sku", sa.String(64), primary_key=True),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("barcode", sa.String(64)),
        sa.Column("dosage_type", sa.String(128)),
        sa.Column("product_type", sa.String(128)),
        sa.Column("size", sa.String(32)),
        sa.Column("status", sa.String(32)),
        sa.Column("rrp", sa.Numeric(10, 2)),
        sa.Column("length_mm", sa.Numeric(10, 2)),
        sa.Column("width_mm", sa.Numeric(10, 2)),
        sa.Column("height_mm", sa.Numeric(10, 2)),
        sa.Column("volume_mm3", sa.Numeric(14, 2)),
        sa.Column("weight_g", sa.Numeric(10, 2)),
        sa.Column("description", sa.Text),
    )

    op.create_table(
        "orders",
        sa.Column("order_no", sa.String(64), primary_key=True),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("company", sa.String(255)),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(255)),
        sa.Column("address_raw", sa.String(512), nullable=False),
        sa.Column("address_line", sa.String(255)),
        sa.Column("suburb", sa.String(128)),
        sa.Column("state", sa.String(8)),
        sa.Column("postcode", sa.String(8)),
    )

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tracking_ref", sa.String(64), nullable=False),
        sa.Column("tracking_no", sa.String(64), nullable=False),
        sa.Column("carrier", sa.String(16), nullable=False),
        sa.Column("logistics_company", sa.String(128), nullable=False),
        sa.UniqueConstraint("tracking_ref", name="uq_shipments_tracking_ref"),
    )

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "order_no",
            sa.String(64),
            sa.ForeignKey("orders.order_no", ondelete="CASCADE", name="fk_order_lines_order"),
            nullable=False,
        ),
        sa.Column("line_no", sa.Integer, nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer),
        sa.Column("quantity_raw", sa.String(64), nullable=False),
        sa.Column(
            "shipment_id",
            sa.Integer,
            sa.ForeignKey("shipments.id", ondelete="SET NULL", name="fk_order_lines_shipment"),
        ),
    )
    op.create_index("ix_order_lines_order_no", "order_lines", ["order_no"])

    op.create_table(
        "shipping_quotes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "order_no",
            sa.String(64),
            sa.ForeignKey("orders.order_no", ondelete="CASCADE", name="fk_shipping_quotes_order"),
            nullable=False,
        ),
        sa.Column(
            "shipment_id",
            sa.Integer,
            sa.ForeignKey("shipments.id", ondelete="CASCADE", name="fk_shipping_quotes_shipment"),
            nullable=False,
        ),
        sa.Column("carrier", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("service_code", sa.String(32)),
        sa.Column("service_name", sa.String(128)),
        sa.Column("fee_ex_gst", sa.Numeric(10, 2), nullable=False),
        sa.Column("fee_incl_gst", sa.Numeric(10, 2), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("source", sa.String(128)),
        sa.Column("parcel", sa.JSON),
        sa.Column(
            "quoted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("order_no", "shipment_id", name="uq_shipping_quotes_order_shipment"),
    )
    op.create_index("ix_shipping_quotes_order_no", "shipping_quotes", ["order_no"])


def downgrade() -> None:
    op.drop_index("ix_shipping_quotes_order_no", table_name="shipping_quotes")
    op.drop_table("shipping_quotes")
    op.drop_index("ix_order_lines_order_no", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_table("shipments")
    op.drop_table("orders")
    op.drop_table("products")
