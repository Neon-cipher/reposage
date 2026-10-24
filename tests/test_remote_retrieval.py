import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from reposage.remote.url_validator import (
    validate_public_repo_url,
    is_ip_private_or_reserved,
    URLValidationError,
)
from reposage.remote.retriever import (
    retrieve_public_repository,
    check_public_repo_accessible,
    verify_downloaded_repo_limits,
    RemoteRetrievalLimits,
    RepoRetrievalError,
    RepoExceedsLimitsError,
)


def test_valid_github_urls():
    urls = [
        "https://github.com/octocat/Hello-World",
        "https://github.com/octocat/Hello-World.git",
        "https://www.github.com/pallets/flask",
        "https://github.com/psf/requests/",
    ]
    for u in urls:
        norm_url, canon_id, prov = validate_public_repo_url(u, resolve_dns=False)
        assert norm_url.endswith(".git")
        assert prov == "github"
        assert "/" in canon_id


def test_malformed_and_unsupported_urls():
    bad_urls = [
        "",
        "not_a_url",
        "ftp://github.com/user/repo",
        "http://github.com/user/repo",  # unencrypted http rejected
        "https://github.com",
        "https://github.com/user",
        "https://github.com/user/repo/extra/path",
        "https://github.com/settings/profile",
    ]
    for bu in bad_urls:
        with pytest.raises(URLValidationError):
            validate_public_repo_url(bu, resolve_dns=False)


def test_embedded_credentials_and_custom_ports_rejected():
    with pytest.raises(URLValidationError) as exc:
        validate_public_repo_url("https://user:token@github.com/user/repo", resolve_dns=False)
    assert "embedded credentials" in str(exc.value).lower()

    with pytest.raises(URLValidationError) as exc2:
        validate_public_repo_url("https://github.com:8080/user/repo", resolve_dns=False)
    assert "unexpected port" in str(exc2.value).lower()


def test_ssrf_and_private_destinations():
    assert is_ip_private_or_reserved("127.0.0.1") is True
    assert is_ip_private_or_reserved("10.0.0.5") is True
    assert is_ip_private_or_reserved("192.168.1.1") is True
    assert is_ip_private_or_reserved("172.16.0.1") is True
    assert is_ip_private_or_reserved("169.254.169.254") is True  # AWS metadata
    assert is_ip_private_or_reserved("8.8.8.8") is False

    # Direct IP destinations
    with pytest.raises(URLValidationError):
        validate_public_repo_url("https://127.0.0.1/user/repo", resolve_dns=False)
    with pytest.raises(URLValidationError):
        validate_public_repo_url("https://169.254.169.254/user/repo", resolve_dns=False)

    # Localhost
    with pytest.raises(URLValidationError):
        validate_public_repo_url("https://localhost/user/repo", resolve_dns=False)


def test_accessibility_check_mock():
    # Public success
    mock_success = MagicMock(returncode=0, stdout="refs/heads/main", stderr="")
    with patch("subprocess.run", return_value=mock_success):
        assert check_public_repo_accessible("https://github.com/user/repo.git") is True

    # Private / Auth failure
    mock_auth_fail = MagicMock(
        returncode=128,
        stdout="",
        stderr="fatal: Authentication failed for 'https://github.com/user/repo.git'",
    )
    with patch("subprocess.run", return_value=mock_auth_fail):
        with pytest.raises(RepoRetrievalError) as exc:
            check_public_repo_accessible("https://github.com/user/repo.git")
        assert "private or requires authentication" in str(exc.value).lower()


def test_temporary_directory_cleanup(tmp_path: Path):
    created_temp_path = None

    # Mock subprocess.run for accessibility check and git clone
    mock_access = MagicMock(returncode=0, stdout="refs/heads/main", stderr="")
    mock_clone = MagicMock(returncode=0, stdout="", stderr="")

    def side_effect_clone(cmd, **kwargs):
        if "ls-remote" in cmd:
            return mock_access
        # For clone, create dummy content in target directory
        target_dir = Path(cmd[-1])
        (target_dir / "README.md").write_text("# Cloned Repo\n", encoding="utf-8")
        return mock_clone

    with patch("subprocess.run", side_effect=side_effect_clone):
        with retrieve_public_repository("https://github.com/octocat/Hello-World") as repo:
            created_temp_path = Path(repo.temp_dir)
            assert created_temp_path.exists()
            assert (created_temp_path / "README.md").exists()
            assert repo.canonical_identity == "octocat/Hello-World"
            assert repo.retrieval_method == "git_shallow_clone"

    # MUST be cleaned up after exiting context
    assert created_temp_path is not None
    assert not created_temp_path.exists()


def test_cleanup_on_error_during_retrieval():
    created_temp = None

    def side_effect_fail(cmd, **kwargs):
        if "ls-remote" in cmd:
            return MagicMock(returncode=0)
        target_dir = Path(cmd[-1])
        target_dir.mkdir(parents=True, exist_ok=True)
        # return error
        return MagicMock(returncode=1, stderr="fatal: repository not found")

    with patch("subprocess.run", side_effect=side_effect_fail):
        with pytest.raises(RepoRetrievalError):
            with retrieve_public_repository("https://github.com/octocat/Hello-World") as repo:
                created_temp = repo.temp_dir

    # Directory was cleaned up
    if created_temp:
        assert not os.path.exists(created_temp)


def test_retrieval_limits(tmp_path: Path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / "file1.txt").write_text("content", encoding="utf-8")
    (d / "file2.txt").write_text("content2", encoding="utf-8")

    limits = RemoteRetrievalLimits(max_total_files=1)
    with pytest.raises(RepoExceedsLimitsError) as exc:
        verify_downloaded_repo_limits(d, limits)
    assert "exceeds file count limit" in str(exc.value).lower()
