from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import CacheDep, CouriersDep, DbSession
from app.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthOut)
async def health(db: DbSession, cache: CacheDep, couriers: CouriersDep) -> HealthOut:
    """Reports which dependencies are reachable/configured. Never exposes secrets."""
    try:
        await db.execute(text("SELECT 1"))
        database = True
    except (SQLAlchemyError, OSError):
        database = False
    redis_ok = await cache.ping()
    return HealthOut(
        status="ok" if database and redis_ok else "degraded",
        database=database,
        redis=redis_ok,
        auspost_configured=couriers.auspost.configured,
        tnt_rtt_configured=couriers.tnt.rtt_configured,
    )
