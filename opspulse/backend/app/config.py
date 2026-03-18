from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "OpsPulse"
    version: str = "1.0.0"
    debug: bool = False

    database_url: str = "postgresql://opspulse:opspulse@localhost:5432/opspulse"

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    anomaly_zscore_threshold: float = 2.5
    anomaly_iqr_multiplier: float = 1.5

    forecast_horizon_days: int = 30
    forecast_confidence: float = 0.95

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
