import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import routers
from app.config import get_settings
from app.db import engine
from app.services.couriers import build_couriers
from app.services.tracking import TrackingCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs full request URLs at INFO; keep it quiet
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    http = httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        headers={"User-Agent": "aeris-order-tracker/0.1"},
    )
    app.state.couriers = build_couriers(settings, http)
    app.state.tracking_cache = TrackingCache(settings.redis_url, settings.tracking_cache_ttl_seconds)
    try:
        yield
    finally:
        await app.state.tracking_cache.close()
        await http.aclose()
        await engine.dispose()


app = FastAPI(
    title="Aeris Order Tracker API",
    description="Order details, GST calculations, shipment fees and courier tracking.",
    version="0.1.0",
    lifespan=lifespan,
)
for router in routers:
    app.include_router(router)
