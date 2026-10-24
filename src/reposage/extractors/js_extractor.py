import re
from typing import List
from reposage.inspector_models import EvidenceRecord, EvidenceType

# Regex for ES Module imports and CommonJS requires
# e.g.: import { a } from 'pkg'; import x from './y'; const a = require('pkg');
ES_IMPORT_RE = re.compile(
    r"""^\s*import\s+(?:(?:\*\s+as\s+[a-zA-Z0-9_$]+|[a-zA-Z0-9_$,\s{}]+)\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
CJS_REQUIRE_RE = re.compile(
    r"""(?:const|let|var)\s+(?:[a-zA-Z0-9_$]+|\{[^}]+\})\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)"""
)

# Common server/app entrypoints
SERVER_LISTEN_RE = re.compile(r"""\.(?:listen|createServer)\s*\(\s*([0-9a-zA-Z_]+|\d+)""")


def extract_js_ts_evidence(rel_path: str, content: str) -> List[EvidenceRecord]:
    """
    Extract imports, entry points, and TODOs from JavaScript/TypeScript source files.
    """
    records: List[EvidenceRecord] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # 1. Imports
        m_es = ES_IMPORT_RE.match(line)
        if m_es:
            source = m_es.group(1)
            records.append(
                EvidenceRecord(
                    relative_path=rel_path,
                    evidence_type=EvidenceType.IMPORT,
                    description=f"ES import from '{source}'",
                    start_line=idx,
                    end_line=idx,
                    snippet=stripped,
                    metadata={"module": source, "language": "javascript/typescript"},
                )
            )
            continue

        m_cjs = CJS_REQUIRE_RE.search(line)
        if m_cjs:
            source = m_cjs.group(1)
            records.append(
                EvidenceRecord(
                    relative_path=rel_path,
                    evidence_type=EvidenceType.IMPORT,
                    description=f"CommonJS require '{source}'",
                    start_line=idx,
                    end_line=idx,
                    snippet=stripped,
                    metadata={"module": source, "language": "javascript/typescript"},
                )
            )
            continue

        # 2. Candidate Entrypoints
        m_listen = SERVER_LISTEN_RE.search(line)
        if m_listen:
            records.append(
                EvidenceRecord(
                    relative_path=rel_path,
                    evidence_type=EvidenceType.ENTRYPOINT,
                    description=f"Server listener entrypoint: {m_listen.group(0)}",
                    start_line=idx,
                    end_line=idx,
                    snippet=stripped,
                    metadata={"entrypoint_type": "server_listen"},
                )
            )

        # 3. TODOs / FIXMEs
        if "//" in stripped or "/*" in stripped:
            upper = stripped.upper()
            for tag in ["TODO", "FIXME", "HACK", "XXX"]:
                if tag in upper:
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.TODO,
                            description=f"Code tag {tag}",
                            start_line=idx,
                            end_line=idx,
                            snippet=stripped,
                            metadata={"tag": tag},
                        )
                    )
                    break

    return records
