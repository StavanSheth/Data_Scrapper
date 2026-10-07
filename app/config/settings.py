"""Application configuration and settings."""

import os
from pydantic_settings import BaseSettings
from app.config.constants import DEFAULT_DB_PATH

class Settings(BaseSettings):
    app_name: str = "Business Intelligence Scraper"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")
    
    # Scraper settings
    request_timeout: int = 30
    max_retries: int = 2
    max_concurrency: int = 2
    default_limit: int = 100
    headless_browser: bool = True
    
    # API settings
    api_prefix: str = "/api"

    model_config = {"env_file": ".env", "extra": "allow"}

settings = Settings()
