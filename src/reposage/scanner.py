import os
from pathlib import Path
from typing import Set, List, Dict, Tuple, Optional
from reposage.models import RepoFacts, TodoItem, CodeCitation

# Directories that must ALWAYS be excluded from scanning
EXCLUDED_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "eggs",
    ".eggs",
    "target",
    "out",
    ".next",
    ".nuxt",
    ".cache",
    "vendor",
    "bin",
    "obj",
}

# Dangerous / Secret filenames to exclude from reading contents
EXCLUDED_FILES: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
}

# Dangerous / Secret file extensions to skip
EXCLUDED_EXTENSIONS: Set[str] = {
    ".pem",
    ".key",
    ".cert",
    ".crt",
    ".pfx",
    ".p12",
    ".keystore",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".war",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".mp4",
    ".mp3",
    ".pdf",
    ".db",
    ".sqlite",
    ".sqlite3",
}

# Recognized language extensions
LANGUAGE_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".json": "JSON",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
    ".sh": "Shell",
    ".bash": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
}

MAX_FILE_SIZE_BYTES = 250_000  # Cap individual file reading at ~250KB to prevent memory exhaustion
MAX_TOTAL_FILES = 1_000        # Safeguard limit


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Ensure target_path does not escape base_dir (prevent directory traversal)."""
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_base or resolved_base in resolved_target.parents
    except Exception:
        return False


def should_skip_path(path: Path) -> bool:
    """Determine if directory or file should be skipped."""
    # Check directory components
    for part in path.parts:
        if part in EXCLUDED_DIRS or (part.startswith(".") and part != "."):
            # Skip hidden folders like .git, .venv, etc.
            if part.startswith(".") and len(part) > 1 and not part.startswith(".github"):
                return True
            if part in EXCLUDED_DIRS:
                return True

    # Check file names and extensions
    if path.is_file():
        name_lower = path.name.lower()
        if name_lower in EXCLUDED_FILES:
            return True
        if name_lower.startswith(".env"):
            return True
        if path.suffix.lower() in EXCLUDED_EXTENSIONS:
            return True

    return False


def scan_repository(repo_path: str, max_files: int = MAX_TOTAL_FILES) -> Tuple[RepoFacts, Dict[str, str]]:
    """
    Deterministically scan repository files, gather structural metrics, and read safe file contents.
    Returns (RepoFacts, Dict[relative_file_path, file_content]).
    """
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid repository directory: {repo_path}")

    facts = RepoFacts(
        root_path=str(root),
        total_files_scanned=0,
        total_lines=0,
    )

    file_contents: Dict[str, str] = {}
    skipped_items: List[str] = []

    # 1. Walk directory tree
    for current_dir, dirs, files in os.walk(root):
        current_path = Path(current_dir)
        
        # In-place modify dirs to avoid traversing excluded subdirectories
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS and not (d.startswith(".") and d not in {".github"})
        ]

        for file in files:
            file_path = current_path / file
            
            # Traversal check
            if not is_safe_path(root, file_path):
                skipped_items.append(f"Security: skipped traversal attempt {file}")
                continue

            if should_skip_path(file_path):
                skipped_items.append(f"Excluded: {file_path.relative_to(root)}")
                continue

            # Check file size
            try:
                stat = file_path.stat()
                if stat.st_size > MAX_FILE_SIZE_BYTES:
                    skipped_items.append(f"Too large ({stat.st_size} bytes): {file_path.relative_to(root)}")
                    continue
            except OSError:
                continue

            rel_path_str = str(file_path.relative_to(root)).replace("\\", "/")
            ext = file_path.suffix.lower()
            lang = LANGUAGE_EXTENSIONS.get(ext, "Other")

            # Try reading file content safely as text
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                skipped_items.append(f"Read error: {rel_path_str} ({e})")
                continue

            # Update facts
            facts.total_files_scanned += 1
            facts.language_counts[lang] = facts.language_counts.get(lang, 0) + 1
            
            lines = content.splitlines()
            line_count = len(lines)
            facts.total_lines += line_count
            facts.language_lines[lang] = facts.language_lines.get(lang, 0) + line_count

            # Check documentation
            lower_name = file_path.name.lower()
            if "readme" in lower_name:
                facts.has_readme = True
                facts.readme_path = rel_path_str
            elif "contributing" in lower_name:
                facts.has_contributing = True
                facts.contributing_path = rel_path_str
            elif "license" in lower_name or "licence" in lower_name:
                facts.has_license = True
                if not facts.license_type:
                    facts.license_type = file_path.name

            # Check config files
            if file_path.name in {
                "pyproject.toml", "setup.py", "requirements.txt", "Pipfile",
                "package.json", "tsconfig.json", "Makefile", "Dockerfile",
                "docker-compose.yml", "docker-compose.yaml", ".gitignore"
            }:
                facts.config_files.append(rel_path_str)

            # Check test files
            if "test" in rel_path_str.lower() or file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
                facts.test_files.append(rel_path_str)
                facts.has_tests = True

            file_contents[rel_path_str] = content

            if facts.total_files_scanned >= max_files:
                skipped_items.append(f"Reached max file limit of {max_files}")
                break
        
        if facts.total_files_scanned >= max_files:
            break

    facts.skipped_items = skipped_items[:100]
    return facts, file_contents
