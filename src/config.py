"""Configuration management for Social Media Limiter."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


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


def load_config() -> Config:
    """Load configuration from file, or return defaults if not found."""
    config_path = get_config_path()

    if not config_path.exists():
        # Return default config with common sites
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

    with open(config_path) as f:
        data = json.load(f)

    return Config.from_dict(data)


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()

    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)


def add_blocked_site(domain: str, subdomains: list[str] | None = None) -> Config:
    """Add a site to the blocked list."""
    config = load_config()

    # Check if already exists
    for site in config.blocked_sites:
        if site.domain == domain:
            return config

    new_site = BlockedSite(domain, subdomains or ["www"])
    config.blocked_sites.append(new_site)
    save_config(config)

    return config


def remove_blocked_site(domain: str) -> Config:
    """Remove a site from the blocked list."""
    config = load_config()
    config.blocked_sites = [site for site in config.blocked_sites if site.domain != domain]
    save_config(config)

    return config
