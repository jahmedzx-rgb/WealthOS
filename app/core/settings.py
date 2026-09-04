from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "WealthOS"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOCAL_USER_ID: int = 1
    WEB_MODE: bool = False
    WEB_SESSION_HOURS: int = 12
    WEB_MAX_USERS: int = 10
    COOKIE_SECURE: bool = True
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver"

    DATABASE_URL: str
    ALPHA_VANTAGE_API_KEY: str | None = None
    MARKET_PRICE_PROVIDER: str = "yahoo"
    MARKET_PRICE_FALLBACK_PROVIDER: str | None = None
    MARKET_PRICE_REQUEST_TIMEOUT_SECONDS: float = 10.0
    MARKET_PRICE_REQUEST_INTERVAL_SECONDS: float = 1.1
    SAHMK_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
