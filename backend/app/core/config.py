from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "app.db"


class Settings(BaseSettings):
    app_name: str = "ACENTRA Fraud Investigation Platform"
    database_url: str = f"sqlite:///{DATABASE_PATH}"
    api_prefix: str = "/api"
    debug: bool = True
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"
    aws_ses_from_email: str | None = None
    aws_sns_topic_arn: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    fraud_alert_admin_email: str | None = None
    smtp_starttls: bool = True
    smtp_ssl: bool = False

    model_config = SettingsConfigDict(env_file=BASE_DIR.parent / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
