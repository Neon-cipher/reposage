import ast
from typing import List, Dict, Tuple
from reposage.models import CodeCitation, TodoItem


def analyze_python_file(
    rel_path: str, content: str
) -> Tuple[List[CodeCitation], List[str], List[TodoItem]]:
    """
    Parse a Python file using the built-in `ast` module.
    Returns:
    - entrypoints: potential main entrypoints (e.g. if __name__ == '__main__')
    - symbols: defined class and function names with line ranges
    - todos: discovered comments with TODO/FIXME tags and line numbers
    """
    entrypoints: List[CodeCitation] = []
    symbols: List[str] = []
    todos: List[TodoItem] = []

    lines = content.splitlines()

    # 1. AST Analysis
    try:
        tree = ast.parse(content, filename=rel_path)
        for node in ast.walk(tree):
            # Detect entry points: if __name__ == "__main__":
            if isinstance(node, ast.If):
                # Check test condition: name == '__main__'
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    if isinstance(left, ast.Name) and left.id == "__name__":
                        for comparator in node.test.comparators:
                            if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                                start_line = getattr(node, "lineno", 1)
                                end_line = getattr(node, "end_lineno", start_line)
                                entrypoints.append(
                                    CodeCitation(
                                        file_path=rel_path,
                                        start_line=start_line,
                                        end_line=end_line,
                                        snippet=lines[start_line - 1] if 0 <= start_line - 1 < len(lines) else None,
                                    )
                                )

            # Extract Function definitions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = getattr(node, "lineno", 1)
                end = getattr(node, "end_lineno", start)
                symbols.append(f"def {node.name}() [L{start}-L{end}]")

            # Extract Class definitions
            elif isinstance(node, ast.ClassDef):
                start = getattr(node, "lineno", 1)
                end = getattr(node, "end_lineno", start)
                symbols.append(f"class {node.name} [L{start}-L{end}]")

    except SyntaxError:
        # Ignore syntax errors in partially formed or different-version files
        pass

    # 2. Extract TODO / FIXME comments
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if "#" in stripped:
            comment_part = stripped[stripped.index("#"):]
            upper_comment = comment_part.upper()
            for tag in ["TODO", "FIXME", "HACK", "XXX", "BUG"]:
                if tag in upper_comment:
                    todos.append(
                        TodoItem(
                            file_path=rel_path,
                            line_number=idx,
                            tag=tag,
                            text=comment_part.lstrip("# ").strip(),
                        )
                    )
                    break

    return entrypoints, symbols, todos
