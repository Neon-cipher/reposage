import os
from pathlib import Path
from typing import Set, Tuple, List, Dict, Optional

from reposage.inspector_models import (
    InspectionLimits,
    DeterministicSummary,
    InspectionResult,
    EvidenceRecord,
    EvidenceType,
)
from reposage.secret_detector import is_secret_file_name, detect_secrets_in_content
from reposage.extractors.python_extractor import extract_python_evidence
from reposage.extractors.js_extractor import extract_js_ts_evidence
from reposage.extractors.manifest_extractor import extract_manifest_and_doc_evidence

# Explicit directories to always exclude
IGNORED_DIR_NAMES: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".coverage",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "target",
    "vendor",
    "bin",
    "obj",
}

# Known text-based file extensions
TEXT_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".json": "JSON",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
    ".conf": "Config",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C Header",
    ".hpp": "C++ Header",
    ".xml": "XML",
}

# Binary and media extensions to strictly ignore
KNOWN_BINARY_EXTENSIONS: Set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".pyc", ".pyo", ".class",
    ".jar", ".war", ".zip", ".tar", ".gz", ".7z", ".rar", ".png", ".jpg",
    ".jpeg", ".gif", ".webp", ".ico", ".svg", ".mp4", ".mp3", ".wav",
    ".pdf", ".db", ".sqlite", ".sqlite3", ".parquet", ".arrow", ".iso",
    ".woff", ".woff2", ".ttf", ".eot",
}


def validate_repository_root(path_str: str) -> Path:
    """Validate that path exists, is a directory, and return resolved Path."""
    if not path_str or not isinstance(path_str, str):
        raise ValueError("Repository path must be a non-empty string.")

    p = Path(path_str)
    if not p.exists():
        raise FileNotFoundError(f"Repository path does not exist: {path_str}")

    resolved = p.resolve()
    if not resolved.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path_str}")

    return resolved


def is_path_contained(root: Path, target: Path) -> bool:
    """Verify target does not escape root (symlinks or traversal)."""
    try:
        resolved_root = root.resolve()
        resolved_target = target.resolve()
        return resolved_target == resolved_root or resolved_root in resolved_target.parents
    except Exception:
        return False


def is_text_file(path: Path) -> bool:
    """Check whether a file is considered an eligible text file."""
    name_lower = path.name.lower()
    suffix_lower = path.suffix.lower()

    if suffix_lower in KNOWN_BINARY_EXTENSIONS:
        return False

    if suffix_lower in TEXT_EXTENSIONS:
        return True

    # Common extensionless text files
    if name_lower in {
        "readme", "license", "licence", "contributing", "makefile",
        "dockerfile", "procfile", "gemfile", "authors", "changelog"
    }:
        return True

    return False


def safely_read_file_text(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely read file text with encoding fallback (utf-8, then utf-8-sig, then latin-1).
    Returns (content, error_or_none).
    """
    try:
        # Check if file has null bytes in first 1024 bytes (binary check)
        with open(path, "rb") as bf:
            chunk = bf.read(1024)
            if b"\x00" in chunk:
                return None, "Binary content (null bytes detected)"

        # Read text
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), None
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return f.read(), None
            except UnicodeDecodeError:
                with open(path, "r", encoding="latin-1") as f:
                    return f.read(), None
    except Exception as e:
        return None, f"Read error: {str(e)}"


def inspect_repository(
    repo_path: str,
    limits: Optional[InspectionLimits] = None,
) -> InspectionResult:
    """
    Purely deterministic, static repository inspection engine.
    - Zero code execution.
    - Safe traversal with symlink breakout prevention.
    - Secret and binary exclusion.
    - Detailed evidence index with exact line ranges and snippets.
    - Summary metrics.
    """
    limits = limits or InspectionLimits()
    root = validate_repository_root(repo_path)

    summary = DeterministicSummary(root_path=str(root), total_files_scanned=0, total_lines=0)
    evidence_index: List[EvidenceRecord] = []
    file_contents: Dict[str, str] = {}
    skipped_items: List[str] = []
    skipped_reasons: Dict[str, int] = {}

    def record_skip(reason: str, rel_path: str):
        skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
        if len(skipped_items) < 150:
            skipped_items.append(f"[{reason}] {rel_path}")

    total_bytes_scanned = 0
    excluded_files_count = 0

    # Walk repository
    for current_dir, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current_dir)

        # Check symlink on current directory
        if current_path.is_symlink():
            if not is_path_contained(root, current_path):
                record_skip("Symlink escaped root", str(current_path))
                dirs[:] = []
                continue

        # Prune excluded directories in-place
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIR_NAMES and not (d.startswith(".") and d != ".github")
        ]

        for file in files:
            file_path = current_path / file
            rel_str = str(file_path.relative_to(root)).replace("\\", "/")

            # 1. Symlink escape check
            if file_path.is_symlink():
                if not is_path_contained(root, file_path):
                    record_skip("Symlink escaped root", rel_str)
                    excluded_files_count += 1
                    continue

            # 2. File count limit check
            if summary.total_files_scanned >= limits.max_files:
                record_skip("Max files limit reached", rel_str)
                excluded_files_count += 1
                break

            # 3. Secret filename check
            is_sec_name, sec_msg = is_secret_file_name(file_path)
            if is_sec_name:
                record_skip(f"Secret excluded ({sec_msg})", rel_str)
                excluded_files_count += 1
                continue

            # 4. Text eligibility check
            if not is_text_file(file_path):
                record_skip("Non-text / binary extension", rel_str)
                excluded_files_count += 1
                continue

            # 5. File size limit check
            try:
                st = file_path.stat()
                if st.st_size > limits.max_file_size_bytes:
                    record_skip(f"File size exceeds limit ({st.st_size} bytes)", rel_str)
                    excluded_files_count += 1
                    continue
                if total_bytes_scanned + st.st_size > limits.max_total_bytes:
                    record_skip("Total repository byte limit exceeded", rel_str)
                    excluded_files_count += 1
                    break
            except OSError as e:
                record_skip(f"Stat error ({e})", rel_str)
                excluded_files_count += 1
                continue

            # 6. Read text safely
            content, read_err = safely_read_file_text(file_path)
            if read_err:
                record_skip(read_err, rel_str)
                excluded_files_count += 1
                continue

            # 7. Secret content check
            is_sec_content, sec_content_msg = detect_secrets_in_content(content)
            if is_sec_content:
                record_skip(f"Secret detected in content ({sec_content_msg})", rel_str)
                excluded_files_count += 1
                continue

            # File accepted into inventory
            summary.total_files_scanned += 1
            total_bytes_scanned += len(content.encode("utf-8", errors="ignore"))
            file_contents[rel_str] = content

            lines = content.splitlines()
            line_count = len(lines)
            summary.total_lines += line_count

            # Language classification
            ext = file_path.suffix.lower()
            lang = TEXT_EXTENSIONS.get(ext, "Other")
            summary.languages_by_count[lang] = summary.languages_by_count.get(lang, 0) + 1
            summary.languages_by_lines[lang] = summary.languages_by_lines.get(lang, 0) + line_count

            # Extract evidence
            file_evidence: List[EvidenceRecord] = []

            # Documentation and manifests
            doc_ev = extract_manifest_and_doc_evidence(rel_str, content)
            file_evidence.extend(doc_ev)

            # Language specific
            if rel_str.endswith(".py"):
                py_ev = extract_python_evidence(rel_str, content)
                file_evidence.extend(py_ev)
            elif rel_str.endswith((".js", ".jsx", ".ts", ".tsx")):
                js_ev = extract_js_ts_evidence(rel_str, content)
                file_evidence.extend(js_ev)

            # Record summary findings
            file_name_lower = file_path.name.lower()
            if "readme" in file_name_lower:
                summary.has_readme = True
                summary.documentation_files.append(rel_str)
            elif "contributing" in file_name_lower:
                summary.has_contributing = True
                summary.documentation_files.append(rel_str)
            elif "license" in file_name_lower or "licence" in file_name_lower:
                summary.has_license = True
                summary.documentation_files.append(rel_str)
            elif rel_str.startswith("docs/"):
                summary.documentation_files.append(rel_str)

            # Test files & test directory
            if "test" in rel_str.lower() or file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
                test_dir = str(file_path.parent.relative_to(root)).replace("\\", "/")
                if test_dir not in summary.test_directories and test_dir != ".":
                    summary.test_directories.append(test_dir)

            # Manifests
            if file_name_lower in {
                "pyproject.toml", "requirements.txt", "setup.py", "package.json",
                "cargo.toml", "go.mod", "pom.xml"
            }:
                if rel_str not in summary.important_manifests:
                    summary.important_manifests.append(rel_str)

            # Cap evidence per file to prevent bloated memory
            for ev in file_evidence[:limits.max_evidence_snippets_per_file]:
                evidence_index.append(ev)

                # Collect commands and entrypoints for summary
                if ev.evidence_type == EvidenceType.RUN_COMMAND:
                    cmd = ev.metadata.get("command", ev.snippet)
                    if cmd and cmd not in summary.candidate_run_commands:
                        summary.candidate_run_commands.append(cmd)
                elif ev.evidence_type == EvidenceType.TEST_COMMAND:
                    cmd = ev.metadata.get("command", ev.snippet)
                    if cmd and cmd not in summary.candidate_test_commands:
                        summary.candidate_test_commands.append(cmd)
                elif ev.evidence_type == EvidenceType.ENTRYPOINT:
                    cit = ev.format_citation()
                    if cit not in summary.candidate_entrypoints:
                        summary.candidate_entrypoints.append(cit)

        if summary.total_files_scanned >= limits.max_files:
            break

    # Calculate documentation coverage score (0.0 to 1.0)
    doc_score = 0.0
    if summary.has_readme:
        doc_score += 0.4
    if summary.has_license:
        doc_score += 0.2
    if summary.has_contributing:
        doc_score += 0.2
    if len(summary.documentation_files) > 3:
        doc_score += 0.2
    elif summary.documentation_files:
        doc_score += 0.1
    summary.documentation_coverage_score = round(min(1.0, doc_score), 2)
    summary.skipped_reasons = skipped_reasons

    return InspectionResult(
        summary=summary,
        evidence_index=evidence_index,
        file_contents=file_contents,
        excluded_files_count=excluded_files_count,
        skipped_items=skipped_items,
    )
