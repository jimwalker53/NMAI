"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the NMIA backend.

    Every field can be overridden by an environment variable of the same name
    (case-insensitive).  Pydantic-settings handles the parsing automatically.
    """

    DATABASE_URL: str = "postgresql://nmia:nmia@localhost:5432/nmia"
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
