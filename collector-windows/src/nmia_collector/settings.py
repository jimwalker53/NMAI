"""
NMIA Windows Collector - Settings

Settings are loaded from environment variables with the NMIA_ prefix,
or from a .env file in the working directory.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Collector configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="NMIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # NMIA server connection
    NMIA_SERVER_URL: str = "http://localhost:8000"
    NMIA_API_KEY: str = ""  # API key for authenticating with the NMIA server

    # Connector identity - UUID of the connector instance registered in NMIA
    CONNECTOR_INSTANCE_ID: str = ""

    # Path to certutil.exe (usually on system PATH on Windows)
    CERTUTIL_PATH: str = "certutil.exe"

    # Logging level
    LOG_LEVEL: str = "INFO"

    # Directory for temporary data files
    DATA_DIR: str = "./data"


settings = Settings()
