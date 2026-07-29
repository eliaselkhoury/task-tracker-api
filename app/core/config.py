"""Application configuration.

Settings are read from environment variables (or a local .env file) so the
same code runs unchanged in development and in tests. See .env.example.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (app/core/config.py -> app -> root).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed application settings with safe defaults."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Path to the JSON file that acts as our database.
    data_file: Path = PROJECT_ROOT / "data" / "tasks.json"

    # Browser origins allowed to call this API. The Live Server default port
    # (5500) is included so the course frontend works out of the box.
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS_ORIGINS value into a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# A single shared settings instance imported by the rest of the app.
settings = Settings()
