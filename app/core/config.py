from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    PROJECT_NAME: str = "LIMS"
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_MINUTES: int = 60
    REFRESH_TOKEN_DAYS: int = 7
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    SH_CLIENT_ID: str = ""
    SH_CLIENT_SECRET: str = ""
    SH_BASE_URL: str = "https://services.sentinel-hub.com"
    SH_TOKEN_URL: str = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"

    @field_validator("DATABASE_URL")
    @classmethod
    def use_asyncpg_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "sslmode=" in v:  # Neon/cloud URLs
            v = v.split("?")[0] + "?ssl=require"
        return v


settings = Settings()
