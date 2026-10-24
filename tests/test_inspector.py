import os
import pytest
from pathlib import Path
from reposage.inspector import (
    inspect_repository,
    validate_repository_root,
    is_path_contained,
    safely_read_file_text,
)
from reposage.inspector_models import InspectionLimits, EvidenceType


def test_validate_repository_root_exceptions(tmp_path: Path):
    with pytest.raises(ValueError):
        validate_repository_root("")

    with pytest.raises(FileNotFoundError):
        validate_repository_root(str(tmp_path / "does_not_exist"))

    file_not_dir = tmp_path / "file.txt"
    file_not_dir.write_text("hello", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        validate_repository_root(str(file_not_dir))


def test_path_containment_and_symlinks(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    inside = root / "inside.py"
    inside.write_text("x = 1", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    secret_outside = outside / "secret.txt"
    secret_outside.write_text("super_secret", encoding="utf-8")

    # Symlink pointing outside root
    symlink_outside = root / "symlink_leak"
    try:
        symlink_outside.symlink_to(secret_outside)
    except (OSError, NotImplementedError):
        # In environments where symlink creation requires admin privileges on Windows
        pass

    assert is_path_contained(root, inside) is True
    assert is_path_contained(root, secret_outside) is False

    result = inspect_repository(str(root))
    assert "inside.py" in result.file_contents
    assert "symlink_leak" not in result.file_contents


def test_ignored_directories(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    # Legitimate source
    (root / "app.py").write_text("print('ok')", encoding="utf-8")

    # Excluded directories
    for ign in [".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "coverage"]:
        d = root / ign
        d.mkdir()
        (d / "dummy.py").write_text("x = 1", encoding="utf-8")

    result = inspect_repository(str(root))
    assert result.summary.total_files_scanned == 1
    assert "app.py" in result.file_contents
    assert not any(ign in k for k in result.file_contents.keys() for ign in [".git", "node_modules", "venv"])


def test_file_size_limits_and_count_limits(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    small_file = root / "small.txt"
    small_file.write_text("short content", encoding="utf-8")

    large_file = root / "large.txt"
    large_file.write_text("A" * 500, encoding="utf-8")

    # Limit to 200 bytes max per file
    limits = InspectionLimits(max_files=10, max_file_size_bytes=200)
    result = inspect_repository(str(root), limits=limits)

    assert result.summary.total_files_scanned == 1
    assert "small.txt" in result.file_contents
    assert "large.txt" not in result.file_contents
    assert result.excluded_files_count >= 1


def test_secret_exclusion_without_printing_values(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    # Secret by name
    (root / ".env").write_text("DB_PASSWORD=1234567890abcdef", encoding="utf-8")
    (root / "id_rsa").write_text("private key", encoding="utf-8")
    (root / "cert.pem").write_text("CERT", encoding="utf-8")

    # Secret by content pattern inside innocent-looking file
    (root / "config.py").write_text("AWS_KEY = 'AKIA1234567890ABCDEF'\n", encoding="utf-8")

    # Normal file
    (root / "clean.py").write_text("name = 'alice'\n", encoding="utf-8")

    result = inspect_repository(str(root))
    assert "clean.py" in result.file_contents
    assert ".env" not in result.file_contents
    assert "id_rsa" not in result.file_contents
    assert "cert.pem" not in result.file_contents
    assert "config.py" not in result.file_contents

    # Verify no secret value was leaked into skipped descriptions or evidence
    for skipped in result.skipped_items:
        assert "1234567890abcdef" not in skipped
        assert "AKIA1234567890ABCDEF" not in skipped


def test_evidence_extraction_and_line_ranges(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    py_content = """# Header comment
import os
from pathlib import Path

def calculate(a, b):
    # TODO: optimize performance
    return a + b

if __name__ == '__main__':
    print(calculate(1, 2))
"""
    (root / "main.py").write_text(py_content, encoding="utf-8")
    (root / "README.md").write_text("# Welcome\nRun with `python main.py`\nTest with `pytest`\n", encoding="utf-8")

    result = inspect_repository(str(root))

    # Verify summary
    assert result.summary.has_readme is True
    assert result.summary.total_lines > 0
    assert any("main.py" in ep for ep in result.summary.candidate_entrypoints)
    assert any("python main.py" in cmd for cmd in result.summary.candidate_run_commands)
    assert any("pytest" in cmd for cmd in result.summary.candidate_test_commands)

    # Verify line ranges on evidence
    ev_types = [e.evidence_type for e in result.evidence_index]
    assert EvidenceType.IMPORT in ev_types
    assert EvidenceType.ENTRYPOINT in ev_types
    assert EvidenceType.TODO in ev_types
    assert EvidenceType.RUN_COMMAND in ev_types
    assert EvidenceType.TEST_COMMAND in ev_types

    # Find import record
    import_rec = next(e for e in result.evidence_index if e.evidence_type == EvidenceType.IMPORT and "import os" in e.description)
    assert import_rec.start_line == 2
    assert import_rec.snippet.strip() == "import os"


def test_malformed_and_binary_files(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    # File with invalid encoding / binary null bytes
    binary_file = root / "data.dat"
    binary_file.write_bytes(b"\x00\x01\x02\x03\xFF\xFE")

    # File with latin-1 characters
    latin_file = root / "latin.txt"
    latin_file.write_bytes("café résumé".encode("latin-1"))

    result = inspect_repository(str(root))
    assert "latin.txt" in result.file_contents
    assert "data.dat" not in result.file_contents
