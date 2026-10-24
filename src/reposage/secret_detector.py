import re
import math
from pathlib import Path
from typing import Tuple, List, Set

# Suspicious file names or prefixes indicating secrets or credentials
SECRET_FILENAME_KEYWORDS: Set[str] = {
    ".env",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "secret",
    "secrets",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "token",
    "tokens",
}

# Explicit extensions for cryptographic material, binary secrets, and keychains
SECRET_EXTENSIONS: Set[str] = {
    ".pem",
    ".key",
    ".pkcs12",
    ".pfx",
    ".p12",
    ".cer",
    ".crt",
    ".der",
    ".kdb",
    ".keystore",
    ".jks",
}

# Content patterns matching high-entropy secrets and credential assignments
SECRET_CONTENT_PATTERNS = [
    re.compile(r"-----BEGIN\s+[A-Z0-9_-]+\s+(?:PRIVATE\s+KEY|CERTIFICATE|SECRET)-----", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|access[_-]?token|secret[_-]?key|auth[_-]?token|password|passwd|client[_-]?secret)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9_]{36,}", re.IGNORECASE),                     # GitHub Personal Access Token
    re.compile(r"gho_[A-Za-z0-9_]{36,}", re.IGNORECASE),                     # GitHub OAuth Token
    re.compile(r"glpat-[A-Za-z0-9\-_]{20,}", re.IGNORECASE),                 # GitLab PAT
    re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),                          # AWS Access Key ID
    re.compile(r"(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}", re.IGNORECASE),  # Stripe keys
    re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}", re.IGNORECASE),            # Slack Token
]


def is_secret_file_name(path: Path) -> Tuple[bool, str]:
    """Check if file name or extension clearly indicates secret material."""
    name_lower = path.name.lower()

    if path.suffix.lower() in SECRET_EXTENSIONS:
        return True, f"Secret extension: {path.suffix.lower()}"

    for kw in SECRET_FILENAME_KEYWORDS:
        if name_lower == kw or name_lower.startswith(f"{kw}.") or name_lower.endswith(f".{kw}"):
            return True, f"Secret filename match: {kw}"

    return False, ""


def calculate_shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy for a given string to spot random tokens."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    frequencies = {}
    for char in data:
        frequencies[char] = frequencies.get(char, 0) + 1
    for count in frequencies.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def detect_secrets_in_content(content: str) -> Tuple[bool, str]:
    """
    Examine file content for private keys, high-entropy tokens, and credential assignments.
    Never prints or stores the secret values.
    """
    # 1. Regex checks
    for pattern in SECRET_CONTENT_PATTERNS:
        match = pattern.search(content)
        if match:
            # We explicitly do NOT return the captured group or value
            return True, "Detected private key or credential assignment pattern"

    # 2. Line-by-line heuristic check for suspected passwords / tokens with high entropy
    for line in content.splitlines()[:500]:  # check up to first 500 lines
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#") or line_clean.startswith("//"):
            continue

        if any(term in line_clean.lower() for term in ["api_key", "secret", "private_key", "password", "token"]):
            # If line has assignment
            if "=" in line_clean or ":" in line_clean:
                parts = re.split(r"[:=]", line_clean, maxsplit=1)
                if len(parts) == 2:
                    val = parts[1].strip().strip("'\" ;")
                    # If value looks like a token (>20 chars, alphanumeric, high entropy)
                    if len(val) >= 20 and not (" " in val):
                        if calculate_shannon_entropy(val) > 3.6:
                            return True, "High-entropy credential detected in assignment"

    return False, ""
