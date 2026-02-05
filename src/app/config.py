"""
Application configuration using pydantic-settings.

This module provides centralized configuration management with:
- Automatic environment variable loading
- Type validation and conversion
- Clear error messages for missing/invalid config
- Support for .env files

Usage:
    from app.config import get_settings

    settings = get_settings()
    print(settings.supabase_url)
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        supabase_url: Supabase project URL (SUPABASE_URL env var)
        supabase_anon_key: Supabase anonymous/public key (SUPABASE_ANON_KEY env var)

    The class automatically:
    - Loads values from environment variables (case-insensitive)
    - Reads from .env file if present
    - Validates that required fields are provided
    - Raises ValidationError with clear messages if config is invalid
    """

    supabase_url: str
    supabase_anon_key: str

    model_config = SettingsConfigDict(
        # Load from .env file automatically
        env_file=".env",
        # Environment variable names are case-insensitive
        case_sensitive=False,
        # Extra fields in .env are ignored (no error)
        extra="ignore",
    )


class ConfigurationError(Exception):
    """Raised when application configuration is invalid or missing."""

    pass


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings (cached singleton).

    Uses lru_cache to ensure settings are only loaded once,
    improving performance and ensuring consistency.

    Returns:
        Settings instance with validated configuration

    Raises:
        ConfigurationError: If required environment variables are missing
    """
    try:
        return Settings()
    except Exception as e:
        # Convert pydantic validation errors to our custom error
        raise ConfigurationError(f"Invalid configuration: {e}") from e
