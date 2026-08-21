import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TrustGuard AI"
    VERSION: str = "2.0"
    ENV: str = os.environ.get("TRUSTGUARD_ENV", "development")

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
        "null"  # Local file:// URI support for development
    ]
    RATE_LIMIT_START: str = "30/minute"
    RATE_LIMIT_HISTORY: str = "5/minute"
    ENABLE_HTTPS_REDIRECT: bool = os.environ.get("ENABLE_HTTPS_REDIRECT", "false").lower() == "true"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


def validate_production_config(settings_obj: Settings | None = None) -> bool:
    """
    🔴 Items 1 & 2: Validates production security configuration at startup.
    Hhalts application startup immediately if insecure defaults or misconfigurations are detected in production.
    """
    s = settings_obj or settings
    if s.ENV.lower() != "production":
        return True

    errors = []
    if not s.JWT_SECRET_KEY or s.JWT_SECRET_KEY == "super-secret-trustguard-key-change-in-production" or len(s.JWT_SECRET_KEY) < 32:
        errors.append("Production requires a strong TRUSTGUARD_JWT_SECRET (min 32 characters, non-default).")

    if not s.ADMIN_PIN or s.ADMIN_PIN == "1234" or len(s.ADMIN_PIN) < 6:
        errors.append("Production requires a strong TRUSTGUARD_ADMIN_PIN (min 6 characters, non-default '1234').")

    if not s.STEP_UP_PIN or s.STEP_UP_PIN == "9999" or len(s.STEP_UP_PIN) < 6:
        errors.append("Production requires a strong TRUSTGUARD_STEP_UP_PIN (min 6 characters, non-default '9999').")

    if not s.DATABASE_URL:
        errors.append("Production requires a non-empty DATABASE_URL.")

    if "null" in s.ALLOWED_ORIGINS or "*" in s.ALLOWED_ORIGINS:
        errors.append("Production ALLOWED_ORIGINS cannot contain 'null' or '*'. Must specify explicit production domain.")

    if not s.ENABLE_HTTPS_REDIRECT:
        errors.append("Production requires ENABLE_HTTPS_REDIRECT=True.")

    if errors:
        error_msg = "🔴 PRODUCTION SECURITY CONFIGURATION FAILURE:\n" + "\n".join(f" - {err}" for err in errors)
        raise RuntimeError(error_msg)

    return True


