"""Tests for configuration module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import (
    BlockedSite,
    Config,
    add_blocked_site,
    load_config,
    remove_blocked_site,
    save_config,
)


class TestBlockedSite:
    """Tests for BlockedSite class."""

    def test_get_all_domains_default(self):
        """Test getting all domains with default subdomain."""
        site = BlockedSite("example.com")
        domains = site.get_all_domains()

        assert "example.com" in domains
        assert "www.example.com" in domains
        assert len(domains) == 2

    def test_get_all_domains_multiple_subdomains(self):
        """Test getting all domains with multiple subdomains."""
        site = BlockedSite("reddit.com", ["www", "old", "i"])
        domains = site.get_all_domains()

        assert "reddit.com" in domains
        assert "www.reddit.com" in domains
        assert "old.reddit.com" in domains
        assert "i.reddit.com" in domains
        assert len(domains) == 4

    def test_to_dict(self):
        """Test serialization to dictionary."""
        site = BlockedSite("youtube.com", ["www", "m"])
        data = site.to_dict()

        assert data["domain"] == "youtube.com"
        assert data["subdomains"] == ["www", "m"]

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"domain": "tiktok.com", "subdomains": ["www"]}
        site = BlockedSite.from_dict(data)

        assert site.domain == "tiktok.com"
        assert site.subdomains == ["www"]


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = Config()

        assert config.daily_limit_seconds == 1800
        assert config.reset_time == "00:00"
        assert config.override_delay_seconds == 300
        assert config.override_grant_seconds == 600
        assert config.launch_at_login is False

    def test_get_all_blocked_domains(self):
        """Test getting all blocked domains from config."""
        config = Config(
            blocked_sites=[
                BlockedSite("youtube.com", ["www", "m"]),
                BlockedSite("reddit.com", ["www"]),
            ]
        )

        domains = config.get_all_blocked_domains()

        assert "youtube.com" in domains
        assert "www.youtube.com" in domains
        assert "m.youtube.com" in domains
        assert "reddit.com" in domains
        assert "www.reddit.com" in domains

    def test_round_trip_serialization(self):
        """Test that config survives serialization round-trip."""
        original = Config(
            daily_limit_seconds=3600,
            reset_time="06:00",
            override_delay_seconds=600,
            override_grant_seconds=1200,
            blocked_sites=[BlockedSite("example.com", ["www", "api"])],
            launch_at_login=True,
        )

        data = original.to_dict()
        restored = Config.from_dict(data)

        assert restored.daily_limit_seconds == original.daily_limit_seconds
        assert restored.reset_time == original.reset_time
        assert restored.override_delay_seconds == original.override_delay_seconds
        assert restored.override_grant_seconds == original.override_grant_seconds
        assert restored.launch_at_login == original.launch_at_login
        assert len(restored.blocked_sites) == len(original.blocked_sites)
        assert restored.blocked_sites[0].domain == "example.com"


class TestConfigPersistence:
    """Tests for config load/save functions."""

    def test_load_config_creates_defaults(self):
        """Test that loading config creates defaults when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.config.get_config_dir", return_value=Path(tmpdir)):
                config = load_config()

                assert config.daily_limit_seconds == 1800
                assert len(config.blocked_sites) > 0

    def test_save_and_load_config(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.config.get_config_dir", return_value=Path(tmpdir)):
                original = Config(
                    daily_limit_seconds=7200,
                    blocked_sites=[BlockedSite("test.com")],
                )

                save_config(original)
                loaded = load_config()

                assert loaded.daily_limit_seconds == 7200
                assert len(loaded.blocked_sites) == 1
                assert loaded.blocked_sites[0].domain == "test.com"
