"""Tests for browser tracking module."""

import pytest

from src.tracker import extract_domain, is_blocked_site


class TestExtractDomain:
    """Tests for domain extraction."""

    def test_simple_url(self):
        """Test extracting domain from simple URL."""
        assert extract_domain("https://youtube.com") == "youtube.com"

    def test_url_with_www(self):
        """Test extracting domain with www prefix."""
        assert extract_domain("https://www.youtube.com") == "www.youtube.com"

    def test_url_with_path(self):
        """Test extracting domain from URL with path."""
        assert extract_domain("https://youtube.com/watch?v=abc123") == "youtube.com"

    def test_url_with_port(self):
        """Test extracting domain from URL with port."""
        assert extract_domain("https://localhost:8080/path") == "localhost"

    def test_subdomain(self):
        """Test extracting subdomain."""
        assert extract_domain("https://old.reddit.com/r/python") == "old.reddit.com"

    def test_invalid_url(self):
        """Test handling invalid URL."""
        assert extract_domain("not a url") is None

    def test_empty_string(self):
        """Test handling empty string."""
        assert extract_domain("") is None


class TestIsBlockedSite:
    """Tests for blocked site detection."""

    def test_exact_match(self):
        """Test exact domain match."""
        blocked = ["youtube.com", "reddit.com"]
        assert is_blocked_site("https://youtube.com", blocked) is True

    def test_subdomain_match(self):
        """Test subdomain matching."""
        blocked = ["youtube.com"]
        assert is_blocked_site("https://www.youtube.com", blocked) is True
        assert is_blocked_site("https://m.youtube.com", blocked) is True

    def test_no_match(self):
        """Test non-matching domain."""
        blocked = ["youtube.com", "reddit.com"]
        assert is_blocked_site("https://google.com", blocked) is False

    def test_partial_match_not_blocked(self):
        """Test that partial matches don't trigger blocking."""
        blocked = ["tube.com"]
        assert is_blocked_site("https://youtube.com", blocked) is False

    def test_empty_blocked_list(self):
        """Test with empty blocked list."""
        assert is_blocked_site("https://youtube.com", []) is False

    def test_blocked_with_path(self):
        """Test blocking works with full URLs."""
        blocked = ["youtube.com"]
        assert is_blocked_site("https://youtube.com/watch?v=abc123", blocked) is True
