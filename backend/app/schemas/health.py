from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    redis: bool
    auspost_configured: bool
    tnt_rtt_configured: bool
