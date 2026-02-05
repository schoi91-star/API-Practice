"""
Supabase client factory module.

Provides a function to create authenticated Supabase client instances
using configuration from environment variables.

Usage:
    from app.supabase_client import get_supabase_client

    client = get_supabase_client()
    response = client.table("my_table").select("*").execute()
"""
from supabase import create_client, Client

from .config import get_settings, ConfigurationError
from .logger import get_logger

logger = get_logger(__name__)


# Re-export ConfigurationError for backwards compatibility
# Allows: from app.supabase_client import SupabaseConfigError
SupabaseConfigError = ConfigurationError


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client using environment variables.

    Uses the centralized Settings class for configuration management,
    which provides:
    - Automatic .env file loading
    - Type validation
    - Clear error messages for missing config

    Returns:
        Authenticated Supabase Client instance

    Raises:
        ConfigurationError: If SUPABASE_URL or SUPABASE_ANON_KEY is not set
    """
    settings = get_settings()

    logger.debug(f"Connecting to Supabase: {settings.supabase_url}")
    return create_client(settings.supabase_url, settings.supabase_anon_key)
