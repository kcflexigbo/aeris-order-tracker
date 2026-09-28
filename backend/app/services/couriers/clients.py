from dataclasses import dataclass

import httpx

from app.config import Settings
from app.services.couriers.auspost import AusPostClient
from app.services.couriers.tnt import TntClient


@dataclass(frozen=True)
class Couriers:
    auspost: AusPostClient
    tnt: TntClient


def build_couriers(settings: Settings, http: httpx.AsyncClient) -> Couriers:
    """Build once per process (app startup) so the shared HTTP connection pool and
    the AusPost concurrency limit apply across all requests."""
    return Couriers(auspost=AusPostClient(settings, http), tnt=TntClient(settings, http))
