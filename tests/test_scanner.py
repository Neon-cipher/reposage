"""Unit tests for scanner."""
import pytest
from pathlib import Path
from reposage.scanner import scan_repository, should_skip_path, is_safe_path


def test_scanner_basic(tmp_path: Path):
    # Setup mock repository
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello world')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")

    facts, contents = scan_repository(str(tmp_path))

    assert facts.total_files_scanned == 3
    assert facts.has_readme is True
    assert facts.has_license is True
    assert "src/main.py" in contents
    assert facts.language_counts.get("Python") == 1
    assert facts.language_counts.get("Markdown") == 1


def test_scanner_exclusion_rules(tmp_path: Path):
    # Create git and venv folders with secret/binary files
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("dummy", encoding="utf-8")

    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("dummy", encoding="utf-8")

    node_dir = tmp_path / "node_modules"
    node_dir.mkdir()
    (node_dir / "pkg.js").write_text("dummy", encoding="utf-8")

    # Secrets and binary
    (tmp_path / ".env").write_text("SECRET=123", encoding="utf-8")
    (tmp_path / "cert.pem").write_text("CERT", encoding="utf-8")
    (tmp_path / "program.exe").write_text("BINARY", encoding="utf-8")

    # Legitimate file
    (tmp_path / "app.py").write_text("a = 1", encoding="utf-8")

    facts, contents = scan_repository(str(tmp_path))

    assert facts.total_files_scanned == 1
    assert "app.py" in contents
    assert ".env" not in contents
    assert "cert.pem" not in contents
    assert "program.exe" not in contents


def test_is_safe_path(tmp_path: Path):
    base = tmp_path / "base"
    base.mkdir()
    child = base / "file.txt"
    outside = tmp_path / "outside.txt"

    assert is_safe_path(base, child) is True
    assert is_safe_path(base, outside) is False
