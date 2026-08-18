import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TrustGuard AI"
    VERSION: str = "2.0"
    ENV: str = "development"
    
    # Security / Auth
    JWT_SECRET_KEY: str = os.environ.get("TRUSTGUARD_JWT_SECRET", "super-secret-trustguard-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_PIN: str = os.environ.get("TRUSTGUARD_ADMIN_PIN", "1234")
    STEP_UP_PIN: str = os.environ.get("TRUSTGUARD_STEP_UP_PIN", "9999")


    # Database & Redis
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))

    # Rate Limiting & Security
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "null"  # Local file:// URI support
    ]
    RATE_LIMIT_START: str = "30/minute"
    RATE_LIMIT_HISTORY: str = "5/minute"
    ENABLE_HTTPS_REDIRECT: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

