import ipaddress
import re
import socket
from typing import Tuple, Optional, Set
from urllib.parse import urlparse

# Explicit hostname allowlist for public providers
ALLOWED_HOSTNAMES: Set[str] = {
    "github.com",
    "www.github.com",
    "gitlab.com",
    "www.gitlab.com",
}

# Regex matching valid GitHub repository paths: /<owner>/<repo> or /<owner>/<repo>.git
GITHUB_REPO_PATH_RE = re.compile(r"^/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+?)(?:\.git)?/?$")
GITLAB_REPO_PATH_RE = re.compile(r"^/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+?)(?:\.git)?/?$")


class URLValidationError(ValueError):
    """Raised when repository URL validation fails or indicates unsafe destination."""
    pass


def is_ip_private_or_reserved(ip_str: str) -> bool:
    """Check if an IP string is private, loopback, link-local, multicast, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def validate_public_repo_url(
    raw_url: str,
    resolve_dns: bool = True,
) -> Tuple[str, str, str]:
    """
    Validate and normalize a public repository URL.
    Enforces:
    - Standard HTTPS protocol only.
    - Explicit hostname allowlist (github.com, gitlab.com).
    - No embedded credentials (user:pass).
    - No custom or unexpected ports.
    - Path must strictly match /<owner>/<repo>.
    - Rejects localhost, loopback, private IP destinations, and internal subnets.
    
    Returns:
    (normalized_clone_url, canonical_repo_identity, provider_name)
    e.g. ("https://github.com/octocat/Hello-World.git", "octocat/Hello-World", "github")
    """
    if not raw_url or not isinstance(raw_url, str):
        raise URLValidationError("Repository URL must be a non-empty string.")

    cleaned_url = raw_url.strip()
    parsed = urlparse(cleaned_url)

    # 1. Protocol check: HTTPS only
    if parsed.scheme.lower() != "https":
        raise URLValidationError(
            f"Unsupported protocol '{parsed.scheme}'. Only public HTTPS repository URLs are allowed."
        )

    # 2. Reject embedded credentials (e.g. https://user:pass@github.com/...)
    if parsed.username or parsed.password:
        raise URLValidationError(
            "URLs with embedded credentials or access tokens are strictly forbidden."
        )

    # 3. Reject unexpected ports
    if parsed.port is not None and parsed.port != 443:
        raise URLValidationError(
            f"Unexpected port '{parsed.port}'. Only default HTTPS (port 443) is allowed."
        )

    # 4. Hostname validation
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise URLValidationError("Missing hostname in repository URL.")

    # Check for direct IP address in hostname (reject direct IP clones)
    try:
        ipaddress.ip_address(hostname)
        raise URLValidationError(
            "Direct IP address destinations are not allowed for public repository analysis."
        )
    except ValueError:
        pass

    # Reject localhost / local domains explicitly
    if hostname in {"localhost", "127.0.0.1", "::1", "local", "internal", "metadata"}:
        raise URLValidationError("Access to localhost or internal hosts is strictly forbidden.")

    # Check explicit allowlist
    if hostname not in ALLOWED_HOSTNAMES:
        raise URLValidationError(
            f"Unsupported repository host '{hostname}'. Only public GitHub (and GitLab) URLs are currently supported."
        )

    # 5. DNS resolution check to prevent SSRF / DNS rebinding to internal addresses
    if resolve_dns:
        try:
            addr_info = socket.getaddrinfo(hostname, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for item in addr_info:
                sockaddr = item[4]
                ip_addr = sockaddr[0]
                if is_ip_private_or_reserved(ip_addr):
                    raise URLValidationError(
                        f"Resolved IP destination '{ip_addr}' for '{hostname}' is a private or reserved network address."
                    )
        except socket.gaierror as e:
            raise URLValidationError(f"Could not resolve host '{hostname}': {e}") from e

    # 6. Path validation & canonical identity extraction
    path = parsed.path
    if "github.com" in hostname:
        match = GITHUB_REPO_PATH_RE.match(path)
        if not match:
            raise URLValidationError(
                "Invalid GitHub repository URL path. Expected format: https://github.com/<owner>/<repo>"
            )
        owner, repo = match.group(1), match.group(2)
        # Disallow reserved GitHub routes (e.g. /settings, /login, /explore)
        if owner.lower() in {"settings", "login", "explore", "pricing", "marketplace", "features", "topics"}:
            raise URLValidationError(f"'{owner}' is a reserved GitHub portal path, not a repository owner.")

        canonical_identity = f"{owner}/{repo}"
        normalized_url = f"https://github.com/{owner}/{repo}.git"
        provider = "github"

    elif "gitlab.com" in hostname:
        match = GITLAB_REPO_PATH_RE.match(path)
        if not match:
            raise URLValidationError(
                "Invalid GitLab repository URL path. Expected format: https://gitlab.com/<owner>/<repo>"
            )
        owner, repo = match.group(1), match.group(2)
        canonical_identity = f"{owner}/{repo}"
        normalized_url = f"https://gitlab.com/{owner}/{repo}.git"
        provider = "gitlab"
    else:
        raise URLValidationError(f"Unsupported provider for host: {hostname}")

    return normalized_url, canonical_identity, provider
