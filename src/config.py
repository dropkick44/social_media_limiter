"""Configuration management for Social Media Limiter."""

import fcntl
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# File lock for thread-safe config operations
_config_lock_fd = None


def _get_lock_path() -> Path:
    """Get the lock file path."""
    return get_config_dir() / "config.lock"


def _acquire_lock() -> int:
    """Acquire exclusive lock for config file operations."""
    global _config_lock_fd
    lock_path = _get_lock_path()
    _config_lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    fcntl.flock(_config_lock_fd, fcntl.LOCK_EX)
    return _config_lock_fd


def _release_lock() -> None:
    """Release the config file lock."""
    global _config_lock_fd
    if _config_lock_fd is not None:
        fcntl.flock(_config_lock_fd, fcntl.LOCK_UN)
        os.close(_config_lock_fd)
        _config_lock_fd = None


@dataclass
class BlockedSite:
    """A site to block with its subdomains."""

    domain: str
    subdomains: list[str] = field(default_factory=lambda: ["www"])

    def get_all_domains(self) -> list[str]:
        """Return all domain variants to block."""
        domains = [self.domain]
        for sub in self.subdomains:
            domains.append(f"{sub}.{self.domain}")
        return domains

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {"domain": self.domain, "subdomains": self.subdomains}

    @classmethod
    def from_dict(cls, data: dict) -> "BlockedSite":
        """Create from dictionary."""
        return cls(domain=data["domain"], subdomains=data.get("subdomains", ["www"]))


@dataclass
class Config:
    """Application configuration."""

    daily_limit_seconds: int = 1800  # 30 minutes
    reset_time: str = "00:00"  # Midnight
    override_delay_seconds: int = 300  # 5 minutes
    override_grant_seconds: int = 600  # 10 minutes
    blocked_sites: list[BlockedSite] = field(default_factory=list)
    launch_at_login: bool = False

    def get_all_blocked_domains(self) -> list[str]:
        """Return all domains to block (including subdomains)."""
        domains = []
        for site in self.blocked_sites:
            domains.extend(site.get_all_domains())
        return domains

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "daily_limit_seconds": self.daily_limit_seconds,
            "reset_time": self.reset_time,
            "override_delay_seconds": self.override_delay_seconds,
            "override_grant_seconds": self.override_grant_seconds,
            "blocked_sites": [site.to_dict() for site in self.blocked_sites],
            "launch_at_login": self.launch_at_login,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create from dictionary."""
        blocked_sites = [BlockedSite.from_dict(site) for site in data.get("blocked_sites", [])]
        return cls(
            daily_limit_seconds=data.get("daily_limit_seconds", 1800),
            reset_time=data.get("reset_time", "00:00"),
            override_delay_seconds=data.get("override_delay_seconds", 300),
            override_grant_seconds=data.get("override_grant_seconds", 600),
            blocked_sites=blocked_sites,
            launch_at_login=data.get("launch_at_login", False),
        )


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_dir = Path.home() / ".config" / "social_limiter"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.json"


def _get_default_config() -> Config:
    """Return default config with common sites."""
    return Config(
        blocked_sites=[
            BlockedSite("youtube.com", ["www", "m"]),
            BlockedSite("reddit.com", ["www", "old", "i", "new"]),
            BlockedSite("twitter.com", ["www", "mobile"]),
            BlockedSite("x.com", ["www"]),
            BlockedSite("instagram.com", ["www"]),
            BlockedSite("tiktok.com", ["www"]),
            BlockedSite("facebook.com", ["www", "m"]),
        ]
    )


def load_config() -> Config:
    """Load configuration from file, or return defaults if not found.

    Thread-safe with file locking.
    """
    config_path = get_config_path()

    _acquire_lock()
    try:
        if not config_path.exists():
            return _get_default_config()

        try:
            with open(config_path) as f:
                data = json.load(f)
            return Config.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Corrupted config file, using defaults: {e}")
            return _get_default_config()
    finally:
        _release_lock()


def _save_config_unlocked(config: Config) -> None:
    """Save config to file atomically. Must be called with lock held."""
    config_path = get_config_path()
    dir_path = config_path.parent

    # Write to temp file first, then atomically rename
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=dir_path, delete=False, suffix=".tmp"
        ) as f:
            json.dump(config.to_dict(), f, indent=2)
            temp_path = f.name

        # Atomic rename on POSIX
        os.rename(temp_path, config_path)
    except OSError as e:
        logger.error(f"Failed to save config: {e}")
        # Clean up temp file if it exists
        if "temp_path" in locals():
            Path(temp_path).unlink(missing_ok=True)
        raise


def save_config(config: Config) -> None:
    """Save configuration to file atomically. Thread-safe with file locking."""
    _acquire_lock()
    try:
        _save_config_unlocked(config)
    finally:
        _release_lock()


def add_blocked_site(domain: str, subdomains: list[str] | None = None) -> Config:
    """Add a site to the blocked list. Thread-safe."""
    _acquire_lock()
    try:
        config_path = get_config_path()

        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                config = Config.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                config = _get_default_config()
        else:
            config = _get_default_config()

        # Check if already exists
        for site in config.blocked_sites:
            if site.domain == domain:
                return config

        new_site = BlockedSite(domain, subdomains or ["www"])
        config.blocked_sites.append(new_site)
        _save_config_unlocked(config)

        return config
    finally:
        _release_lock()


def remove_blocked_site(domain: str) -> Config:
    """Remove a site from the blocked list. Thread-safe."""
    _acquire_lock()
    try:
        config_path = get_config_path()

        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                config = Config.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                config = _get_default_config()
        else:
            config = _get_default_config()

        config.blocked_sites = [site for site in config.blocked_sites if site.domain != domain]
        _save_config_unlocked(config)

        return config
    finally:
        _release_lock()
