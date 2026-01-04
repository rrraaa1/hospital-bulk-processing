"""
Application configuration and settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # API Configuration
    HOSPITAL_API_URL: str = "https://hospital-directory.onrender.com"
    API_TIMEOUT: int = 30  # seconds

    # Processing Limits
    MAX_HOSPITALS_PER_BATCH: int = 20
    MAX_FILE_SIZE_MB: int = 5

    # CSV Configuration
    REQUIRED_CSV_COLUMNS: list = ["name", "address"]
    OPTIONAL_CSV_COLUMNS: list = ["phone"]

    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds

    # Application Settings
    APP_NAME: str = "Hospital Bulk Processing API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # CORS Settings
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()