import ast
import re
from typing import List, Tuple
from reposage.inspector_models import EvidenceRecord, EvidenceType


def extract_python_evidence(rel_path: str, content: str) -> List[EvidenceRecord]:
    """
    Extract imports, candidate entry points, and definitions with line ranges from Python code.
    Uses Python's ast module, falling back to regex on syntax errors.
    """
    records: List[EvidenceRecord] = []
    lines = content.splitlines()

    def get_snippet(s_line: int, e_line: int) -> str:
        s_idx = max(0, s_line - 1)
        e_idx = min(len(lines), e_line)
        return "\n".join(lines[s_idx:e_idx])

    try:
        tree = ast.parse(content, filename=rel_path)

        for node in ast.walk(tree):
            # 1. Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    s = getattr(node, "lineno", 1)
                    e = getattr(node, "end_lineno", s)
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.IMPORT,
                            description=f"import {alias.name}",
                            start_line=s,
                            end_line=e,
                            snippet=get_snippet(s, e),
                            metadata={"module": alias.name, "language": "python"},
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = ", ".join(a.name for a in node.names)
                s = getattr(node, "lineno", 1)
                e = getattr(node, "end_lineno", s)
                records.append(
                    EvidenceRecord(
                        relative_path=rel_path,
                        evidence_type=EvidenceType.IMPORT,
                        description=f"from {mod} import {names}",
                        start_line=s,
                        end_line=e,
                        snippet=get_snippet(s, e),
                        metadata={"module": mod, "names": names, "language": "python"},
                    )
                )

            # 2. Candidate Entrypoints (if __name__ == '__main__': or cli entrypoints)
            elif isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    if isinstance(left, ast.Name) and left.id == "__name__":
                        for cmp in node.test.comparators:
                            if isinstance(cmp, ast.Constant) and cmp.value == "__main__":
                                s = getattr(node, "lineno", 1)
                                e = getattr(node, "end_lineno", s)
                                records.append(
                                    EvidenceRecord(
                                        relative_path=rel_path,
                                        evidence_type=EvidenceType.ENTRYPOINT,
                                        description="Python standard main entrypoint guard",
                                        start_line=s,
                                        end_line=min(s + 3, e),
                                        snippet=get_snippet(s, min(s + 3, e)),
                                        metadata={"entrypoint_type": "name_main"},
                                    )
                                )

            # 3. Code Symbols (Classes and Functions)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                s = getattr(node, "lineno", 1)
                e = getattr(node, "end_lineno", s)
                # Check for cli click or argparse or fast api decorators
                is_endpoint = False
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Name):
                            dec_name = dec.func.id
                        elif isinstance(dec.func, ast.Attribute):
                            dec_name = dec.func.attr
                    if dec_name.lower() in {"get", "post", "put", "delete", "command", "route"}:
                        is_endpoint = True
                        break

                if is_endpoint:
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.ENTRYPOINT,
                            description=f"Web/CLI routing entrypoint: def {node.name}()",
                            start_line=s,
                            end_line=s,
                            snippet=get_snippet(s, s),
                            metadata={"symbol": node.name},
                        )
                    )
                else:
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.CODE_SYMBOL,
                            description=f"Function definition: def {node.name}()",
                            start_line=s,
                            end_line=s,
                            snippet=get_snippet(s, s),
                            metadata={"symbol": node.name, "type": "function"},
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                s = getattr(node, "lineno", 1)
                records.append(
                    EvidenceRecord(
                        relative_path=rel_path,
                        evidence_type=EvidenceType.CODE_SYMBOL,
                        description=f"Class definition: class {node.name}",
                        start_line=s,
                        end_line=s,
                        snippet=get_snippet(s, s),
                        metadata={"symbol": node.name, "type": "class"},
                    )
                )

    except SyntaxError:
        # Fallback regex extraction if ast fails
        import_re = re.compile(r"^\s*(?:from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\.]+))")
        for idx, line in enumerate(lines, start=1):
            m = import_re.match(line)
            if m:
                mod = m.group(1) or m.group(2)
                records.append(
                    EvidenceRecord(
                        relative_path=rel_path,
                        evidence_type=EvidenceType.IMPORT,
                        description=f"import {mod} (fallback)",
                        start_line=idx,
                        end_line=idx,
                        snippet=line,
                        metadata={"module": mod, "language": "python"},
                    )
                )

    # 4. Check for TODOs
    for idx, line in enumerate(lines, start=1):
        if "#" in line:
            c = line[line.index("#"):].strip()
            upper = c.upper()
            for tag in ["TODO", "FIXME", "HACK", "XXX"]:
                if tag in upper:
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.TODO,
                            description=f"Code tag {tag}",
                            start_line=idx,
                            end_line=idx,
                            snippet=line.strip(),
                            metadata={"tag": tag},
                        )
                    )
                    break

    return records
