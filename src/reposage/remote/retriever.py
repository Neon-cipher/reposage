import os
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, Generator, Tuple
from contextlib import contextmanager

from reposage.remote.url_validator import validate_public_repo_url, URLValidationError


class RepoRetrievalError(RuntimeError):
    """Raised when repository cloning, downloading, or extraction fails."""
    pass


class RepoExceedsLimitsError(RepoRetrievalError):
    """Raised when cloned/downloaded repository exceeds configured safety limits."""
    pass


@dataclass
class RemoteRetrievalLimits:
    """Configurable boundaries for remote repository cloning and storage."""
    max_download_size_bytes: int = 50_000_000  # 50 MB total limit for downloaded folder
    max_total_files: int = 2_000               # 2000 files limit
    clone_timeout_seconds: int = 60            # 60s timeout for git clone
    submodules: bool = False                   # Strictly forbid submodules


@dataclass
class RetrievedRepo:
    """Result of safely retrieving a public repository into an isolated temporary directory."""
    temp_dir: str
    canonical_identity: str
    normalized_url: str
    provider: str
    retrieval_method: str
    total_files_downloaded: int
    total_size_bytes: int


def check_public_repo_accessible(normalized_url: str, timeout_sec: int = 10) -> bool:
    """
    Check if public repository is genuinely accessible without authentication.
    Uses 'git ls-remote' with GIT_TERMINAL_PROMPT=0 so private repos immediately fail.
    """
    cmd = ["git", "ls-remote", "--heads", normalized_url]
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"  # Prevent interactive password prompt

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return True
        # If exit code != 0, check if it's an auth or not found failure
        stderr_lower = proc.stderr.lower()
        if "authentication failed" in stderr_lower or "could not read username" in stderr_lower:
            raise RepoRetrievalError(
                "Repository is private or requires authentication. RepoSage only analyzes public repositories."
            )
        if "not found" in stderr_lower or "repository not found" in stderr_lower:
            raise RepoRetrievalError("Public repository not found (404). Check the owner and repo name.")

        raise RepoRetrievalError(f"Could not access remote repository: {proc.stderr.strip()[:200]}")
    except subprocess.TimeoutExpired as e:
        raise RepoRetrievalError("Timed out while verifying remote repository accessibility.") from e
    except Exception as e:
        if isinstance(e, RepoRetrievalError):
            raise
        raise RepoRetrievalError(f"Error checking remote repository accessibility: {str(e)}") from e


def verify_downloaded_repo_limits(
    target_path: Path,
    limits: RemoteRetrievalLimits,
) -> Tuple[int, int]:
    """
    Verify that downloaded repository does not exceed size and file count limits.
    Returns (file_count, total_bytes).
    """
    total_files = 0
    total_bytes = 0

    for current_dir, dirs, files in os.walk(target_path):
        for f in files:
            fp = Path(current_dir) / f
            total_files += 1
            if total_files > limits.max_total_files:
                raise RepoExceedsLimitsError(
                    f"Repository exceeds file count limit ({limits.max_total_files} files)."
                )
            try:
                sz = fp.stat().st_size
                total_bytes += sz
                if total_bytes > limits.max_download_size_bytes:
                    raise RepoExceedsLimitsError(
                        f"Repository download size exceeds limit of {limits.max_download_size_bytes / (1024*1024):.1f} MB."
                    )
            except OSError:
                pass

    return total_files, total_bytes


@contextmanager
def retrieve_public_repository(
    repo_url: str,
    limits: Optional[RemoteRetrievalLimits] = None,
    verify_accessibility: bool = True,
) -> Generator[RetrievedRepo, None, None]:
    """
    Safely retrieve a public repository into an isolated temporary directory.
    - Validates URL and prevents SSRF.
    - Verifies public accessibility without authentication prompts.
    - Performs a shallow, single-branch clone (depth 1, no submodules).
    - Checks limits (total files, download size).
    - Cleans up temporary storage automatically upon exit or error.
    """
    limits = limits or RemoteRetrievalLimits()

    # Step 1: Validate URL
    normalized_url, canonical_id, provider = validate_public_repo_url(repo_url)

    # Step 2: Check accessibility
    if verify_accessibility:
        check_public_repo_accessible(normalized_url)

    # Step 3: Create unique temporary directory
    temp_dir = tempfile.mkdtemp(prefix=f"reposage_remote_{canonical_id.replace('/', '_')}_")

    try:
        # Step 4: Execute shallow single-branch git clone
        # Hardened git parameters: depth 1, single branch, disable hooks
        clone_cmd = [
            "git",
            "clone",
            "--depth", "1",
            "--single-branch",
            "--no-tags",
            "--config", "core.hooksPath=/dev/null",  # Never run hooks
            normalized_url,
            temp_dir,
        ]

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = "echo"

        proc = subprocess.run(
            clone_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=limits.clone_timeout_seconds,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            err_msg = proc.stderr.strip()[:300]
            if "authentication failed" in err_msg.lower() or "could not read username" in err_msg.lower():
                raise RepoRetrievalError("Repository requires authentication or is private.")
            raise RepoRetrievalError(f"Git clone failed: {err_msg}")

        # Step 5: Verify size & count limits
        file_count, total_bytes = verify_downloaded_repo_limits(Path(temp_dir), limits)

        retrieved = RetrievedRepo(
            temp_dir=temp_dir,
            canonical_identity=canonical_id,
            normalized_url=normalized_url,
            provider=provider,
            retrieval_method="git_shallow_clone",
            total_files_downloaded=file_count,
            total_size_bytes=total_bytes,
        )

        yield retrieved

    finally:
        # Step 6: Safe Cleanup
        # Remove write-protection on windows git files if needed
        def handle_remove_readonly(func, path, exc_info):
            try:
                os.chmod(path, 0o777)
                func(path)
            except Exception:
                pass

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
