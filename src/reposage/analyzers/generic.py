import re
import json
from typing import List, Tuple, Dict
from reposage.models import CodeCitation, TodoItem


def analyze_generic_file(
    rel_path: str, content: str
) -> Tuple[List[CodeCitation], List[str], List[TodoItem]]:
    """
    Regex and heuristic parser for JavaScript/TypeScript and generic files.
    Extracts entrypoints, declared functions/classes, and TODOs.
    """
    entrypoints: List[CodeCitation] = []
    symbols: List[str] = []
    todos: List[TodoItem] = []

    lines = content.splitlines()

    # Pattern for JS/TS function / class declarations
    func_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)")
    class_pattern = re.compile(r"^\s*(?:export\s+)?class\s+([a-zA-Z0-9_$]+)")
    const_func_pattern = re.compile(r"^\s*(?:export\s+)?const\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(")

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check for TODO / FIXME comments
        if "//" in stripped or "/*" in stripped or "#" in stripped:
            comment_text = stripped
            upper = comment_text.upper()
            for tag in ["TODO", "FIXME", "HACK", "XXX", "BUG"]:
                if tag in upper:
                    clean_comment = re.sub(r"^[/\\*#\s]+", "", stripped)
                    todos.append(
                        TodoItem(
                            file_path=rel_path,
                            line_number=idx,
                            tag=tag,
                            text=clean_comment,
                        )
                    )
                    break

        # Check JS/TS symbols
        match_fn = func_pattern.match(line)
        if match_fn:
            symbols.append(f"function {match_fn.group(1)}() [L{idx}]")
            continue

        match_cls = class_pattern.match(line)
        if match_cls:
            symbols.append(f"class {match_cls.group(1)} [L{idx}]")
            continue

        match_cfn = const_func_pattern.match(line)
        if match_cfn:
            symbols.append(f"const {match_cfn.group(1)} = () [L{idx}]")
            continue

        # Look for typical server listen / entry points (express, fastify, etc.)
        if ".listen(" in stripped or "createServer(" in stripped:
            entrypoints.append(
                CodeCitation(
                    file_path=rel_path,
                    start_line=idx,
                    end_line=idx,
                    snippet=stripped,
                )
            )

    return entrypoints, symbols, todos


def extract_package_dependencies(rel_path: str, content: str) -> List[str]:
    """Extract declared dependencies from package.json, requirements.txt, or pyproject.toml."""
    deps: List[str] = []
    file_name = rel_path.split("/")[-1].lower()

    if file_name == "package.json":
        try:
            data = json.loads(content)
            for key in ["dependencies", "devDependencies"]:
                if key in data and isinstance(data[key], dict):
                    deps.extend([f"{k}@{v}" for k, v in data[key].items()])
        except Exception:
            pass

    elif file_name == "requirements.txt":
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                deps.append(line)

    elif file_name == "pyproject.toml":
        # Basic heuristic parsing without requiring tomllib if older
        in_deps = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if line.endswith("]"):
                    in_deps = False
                    continue
                cleaned = line.strip('",\' ')
                if cleaned:
                    deps.append(cleaned)

    return deps
