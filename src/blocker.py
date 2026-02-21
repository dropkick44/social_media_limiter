"""Hosts file manipulation for blocking sites."""

import logging
import shlex
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

HOSTS_PATH = Path("/etc/hosts")
BLOCK_START_MARKER = "# -- SocialLimiter Start --"
BLOCK_END_MARKER = "# -- SocialLimiter End --"
REDIRECT_IP = "127.0.0.1"


def read_hosts_file() -> str:
    """Read the current hosts file content."""
    return HOSTS_PATH.read_text()


def get_block_entries(domains: list[str]) -> str:
    """Generate hosts file entries for blocking domains."""
    lines = [BLOCK_START_MARKER]
    for domain in sorted(set(domains)):
        lines.append(f"{REDIRECT_IP}    {domain}")
    lines.append(BLOCK_END_MARKER)
    return "\n".join(lines)


def remove_existing_blocks(content: str) -> str:
    """Remove existing SocialLimiter blocks from hosts content."""
    lines = content.split("\n")
    result = []
    in_block = False

    for line in lines:
        if BLOCK_START_MARKER in line:
            in_block = True
            continue
        if BLOCK_END_MARKER in line:
            in_block = False
            continue
        if not in_block:
            result.append(line)

    # Remove trailing empty lines that might accumulate
    while result and result[-1] == "":
        result.pop()

    return "\n".join(result)


def is_blocking_active() -> bool:
    """Check if SocialLimiter blocks are currently in the hosts file."""
    try:
        content = read_hosts_file()
        return BLOCK_START_MARKER in content
    except PermissionError:
        return False


def get_currently_blocked_domains() -> list[str]:
    """Get list of domains currently blocked in hosts file."""
    try:
        content = read_hosts_file()
    except PermissionError:
        return []

    domains = []
    in_block = False

    for line in content.split("\n"):
        if BLOCK_START_MARKER in line:
            in_block = True
            continue
        if BLOCK_END_MARKER in line:
            in_block = False
            continue
        if in_block and line.strip():
            # Parse "127.0.0.1    domain.com"
            parts = line.split()
            if len(parts) >= 2:
                domains.append(parts[1])

    return domains


def write_hosts_with_sudo(new_content: str) -> bool:
    """Write new hosts file content using sudo via osascript."""
    temp_path = None
    try:
        # Write to temp file first
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".hosts") as f:
            f.write(new_content)
            temp_path = f.name

        # Use osascript to run sudo command with password prompt
        # Use shlex.quote to prevent command injection
        safe_temp_path = shlex.quote(temp_path)
        script = f'''
        do shell script "cp {safe_temp_path} /etc/hosts" with administrator privileges
        '''

        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        # User cancelled or auth failed
        logger.warning("Failed to write hosts file - user cancelled or auth failed")
        return False
    except OSError as e:
        logger.error(f"Failed to write temp file: {e}")
        return False
    finally:
        # Always clean up temp file
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def flush_dns_cache() -> bool:
    """Flush the DNS cache to apply hosts changes immediately."""
    script = '''
    do shell script "dscacheutil -flushcache; killall -HUP mDNSResponder" with administrator privileges
    '''

    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def block_sites(domains: list[str]) -> tuple[bool, bool]:
    """Add domains to the hosts file to block them.

    Returns:
        Tuple of (hosts_modified, dns_flushed). Both should be True for full success.
    """
    if not domains:
        return True, True

    try:
        current_content = read_hosts_file()
    except PermissionError:
        logger.error("Permission denied reading hosts file")
        return False, False

    # Remove any existing blocks first
    clean_content = remove_existing_blocks(current_content)

    # Add new blocks
    block_entries = get_block_entries(domains)
    new_content = clean_content.rstrip() + "\n\n" + block_entries + "\n"

    # Write with sudo
    if not write_hosts_with_sudo(new_content):
        return False, False

    # Flush DNS cache
    dns_flushed = flush_dns_cache()
    if not dns_flushed:
        logger.warning("DNS cache flush failed - blocking may be delayed")

    return True, dns_flushed


def unblock_sites() -> tuple[bool, bool]:
    """Remove all SocialLimiter blocks from the hosts file.

    Returns:
        Tuple of (hosts_modified, dns_flushed). Both should be True for full success.
    """
    try:
        current_content = read_hosts_file()
    except PermissionError:
        logger.error("Permission denied reading hosts file")
        return False, False

    # Check if there's anything to remove
    if BLOCK_START_MARKER not in current_content:
        return True, True

    # Remove blocks
    clean_content = remove_existing_blocks(current_content)
    new_content = clean_content.rstrip() + "\n"

    # Write with sudo
    if not write_hosts_with_sudo(new_content):
        return False, False

    # Flush DNS cache
    dns_flushed = flush_dns_cache()
    if not dns_flushed:
        logger.warning("DNS cache flush failed - unblocking may be delayed")

    return True, dns_flushed
