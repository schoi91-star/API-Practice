import os

from dotenv import load_dotenv
from supabase import create_client, Client

from .logger import get_logger

logger = get_logger(__name__)


class SupabaseConfigError(Exception):
    """Raised when Supabase configuration is missing or invalid."""
    pass


def get_supabase_client() -> Client:
    """Create and return a Supabase client using environment variables."""
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url:
        raise SupabaseConfigError("SUPABASE_URL environment variable is not set")
    if not key:
        raise SupabaseConfigError("SUPABASE_ANON_KEY environment variable is not set")

    logger.debug(f"Connecting to Supabase: {url}")
    return create_client(url, key)
