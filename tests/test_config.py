"""
Unit tests for the config module.

Tests the Settings class and get_settings() function to ensure:
- Environment variables are properly loaded
- Missing config raises appropriate errors
- Settings caching works correctly
"""
import os
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pydantic import ValidationError
from app.config import Settings, ConfigurationError, get_settings


class TestSettings:
    """Tests for the Settings class."""

    def test_settings_loads_from_env_vars(self, monkeypatch):
        """
        Verify Settings correctly loads values from environment variables.
        Uses monkeypatch to set test environment variables.
        """
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-key-123")

        # Create fresh Settings instance without .env file
        settings = Settings(_env_file=None)

        assert settings.supabase_url == "https://test.supabase.co"
        assert settings.supabase_anon_key == "test-key-123"

    def test_settings_case_insensitive(self, monkeypatch):
        """
        Verify environment variable names are case-insensitive.
        Lowercase env var names should work the same as uppercase.
        """
        monkeypatch.setenv("supabase_url", "https://lower.supabase.co")
        monkeypatch.setenv("supabase_anon_key", "lower-key")

        settings = Settings(_env_file=None)

        assert settings.supabase_url == "https://lower.supabase.co"
        assert settings.supabase_anon_key == "lower-key"

    def test_settings_missing_url_raises_error(self, monkeypatch):
        """
        Verify missing SUPABASE_URL raises validation error.
        pydantic-settings should fail when required fields are missing.
        """
        # Clear env vars that might exist
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "key-only")

        # Disable .env file loading to test pure env var behavior
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_settings_missing_key_raises_error(self, monkeypatch):
        """
        Verify missing SUPABASE_ANON_KEY raises validation error.
        """
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")

        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_settings_missing_all_raises_error(self, monkeypatch):
        """
        Verify missing all required fields raises validation error.
        """
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

        with pytest.raises(ValidationError):
            Settings(_env_file=None)


class TestGetSettings:
    """Tests for the get_settings() function."""

    def test_get_settings_returns_settings_instance(self):
        """
        Verify get_settings() returns a Settings instance.
        Requires valid env vars (uses real .env file in test environment).
        """
        # Clear the cache to ensure fresh load
        get_settings.cache_clear()

        settings = get_settings()

        assert isinstance(settings, Settings)
        assert settings.supabase_url is not None
        assert settings.supabase_anon_key is not None

    def test_get_settings_is_cached(self):
        """
        Verify get_settings() returns the same cached instance.
        Multiple calls should return the exact same object (identity check).
        """
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the exact same object (not just equal values)
        assert settings1 is settings2

    def test_settings_url_is_string(self):
        """
        Verify supabase_url is a valid string.
        Integration check with real .env configuration.
        """
        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings.supabase_url, str)
        assert settings.supabase_url.startswith("http")

    def test_settings_key_is_string(self):
        """
        Verify supabase_anon_key is a valid string.
        Integration check with real .env configuration.
        """
        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings.supabase_anon_key, str)
        assert len(settings.supabase_anon_key) > 0
