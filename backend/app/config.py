from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (.env via docker compose)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://aeris:aeris@localhost:5432/aeris"
    redis_url: str = "redis://localhost:6379/0"
    data_dir: str = "../data"
    tracking_cache_ttl_seconds: int = 600
    http_timeout_seconds: float = 15.0

    auspost_base_url: str = "https://digitalapi.auspost.com.au/test/shipping/v1"
    auspost_api_key: str = ""
    auspost_password: str = ""
    auspost_account_number_domestic: str = ""
    auspost_account_number_startrack: str = ""
    startrack_product_id: str = "EXP"

    tnt_tracking_url: str = "https://www.tntexpress.com.au/InterAction/ASPs/CnmHxAS.asp"
    tnt_rtt_url: str = ""
    tnt_uat_username: str = ""
    tnt_uat_password: str = ""
    tnt_uat_account: str = ""
    tnt_service_code: str = "76"
    tnt_price_includes_gst: bool = False

    origin_postcode: str = "2111"
    origin_suburb: str = "GLADESVILLE"
    origin_state: str = "NSW"
    packing_factor: Decimal = Decimal("1.25")
    packaging_weight_kg: Decimal = Decimal("0.3")


@lru_cache
def get_settings() -> Settings:
    return Settings()
