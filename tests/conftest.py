"""
pytest configuration file.

This file is automatically recognized by pytest and defines
shared fixtures and settings used across all tests.
"""
import sys
from pathlib import Path

import pytest

# Add src folder to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.supabase_client import get_supabase_client


@pytest.fixture(scope="session")
def supabase_client():
    """
    Fixture that provides a Supabase client for integration tests.

    scope="session" means this client is created once and shared
    across all tests in the test session.
    """
    return get_supabase_client()
