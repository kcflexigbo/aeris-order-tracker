from fastapi import APIRouter, HTTPException

from app.api.deps import CouriersDep, DbSession, SettingsDep
from app.models import Order
from app.schemas import OrderDetail, OrderSummary
from app.services.orders import build_order_detail, list_orders, load_order

router = APIRouter(prefix="/api/orders", tags=["orders"])


async def _get_order(db: DbSession, order_no: str) -> Order:
    order = await load_order(db, order_no)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_no} not found")
    return order


@router.get("", response_model=list[OrderSummary])
async def get_orders(db: DbSession) -> list[OrderSummary]:
    return await list_orders(db)


@router.get("/{order_no}", response_model=OrderDetail)
async def get_order(order_no: str, db: DbSession, couriers: CouriersDep, settings: SettingsDep) -> OrderDetail:
    """Order header, priced lines, per-shipment quotes (stored; quoted on first view) and totals."""
    order = await _get_order(db, order_no)
    return await build_order_detail(db, order, couriers, settings)


@router.post("/{order_no}/shipping/refresh", response_model=OrderDetail)
async def refresh_shipping(
    order_no: str, db: DbSession, couriers: CouriersDep, settings: SettingsDep
) -> OrderDetail:
    """Re-quote every shipment of the order with the carriers."""
    order = await _get_order(db, order_no)
    return await build_order_detail(db, order, couriers, settings, refresh_quotes=True)
