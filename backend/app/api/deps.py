"""FastAPI dependencies. Long-lived clients are created once in the app lifespan
(app/main.py) and stored on app.state, so every request shares one HTTP
connection pool, one AusPost concurrency limit and one Redis connection pool."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.services.couriers import Couriers
from app.services.tracking import TrackingCache


def get_couriers(request: Request) -> Couriers:
    return request.app.state.couriers


def get_cache(request: Request) -> TrackingCache:
    return request.app.state.tracking_cache


DbSession = Annotated[AsyncSession, Depends(get_db)]
CouriersDep = Annotated[Couriers, Depends(get_couriers)]
CacheDep = Annotated[TrackingCache, Depends(get_cache)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
