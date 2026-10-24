import re
import json
from typing import List, Tuple
from reposage.inspector_models import EvidenceRecord, EvidenceType

# Regex for common run commands documented in markdown/rst
RUN_CMD_PATTERNS = [
    re.compile(r"(?:python|python3|py)\s+([a-zA-Z0-9_\-\./\\]+\.py(?:\s+[^\n`]+)?)", re.IGNORECASE),
    re.compile(r"(?:streamlit\s+run)\s+([^\n`]+)", re.IGNORECASE),
    re.compile(r"(?:npm\s+start|npm\s+run\s+[a-zA-Z0-9_\-]+)", re.IGNORECASE),
    re.compile(r"(?:yarn\s+start|pnpm\s+start)", re.IGNORECASE),
    re.compile(r"(?:uvicorn\s+[a-zA-Z0-9_\.:]+\s+--[^\n`]+|uvicorn\s+[a-zA-Z0-9_\.:]+)", re.IGNORECASE),
    re.compile(r"(?:flask\s+run|fastapi\s+dev)", re.IGNORECASE),
]

TEST_CMD_PATTERNS = [
    re.compile(r"(?:pytest(?:\s+[^\n`]+)?)", re.IGNORECASE),
    re.compile(r"(?:python\s+-m\s+unittest(?:\s+[^\n`]+)?)", re.IGNORECASE),
    re.compile(r"(?:npm\s+test|yarn\s+test|pnpm\s+test)", re.IGNORECASE),
    re.compile(r"(?:jest(?:\s+[^\n`]+)?)", re.IGNORECASE),
    re.compile(r"(?:cargo\s+test|go\s+test)", re.IGNORECASE),
]


def extract_manifest_and_doc_evidence(rel_path: str, content: str) -> List[EvidenceRecord]:
    """
    Extract manifests, dependencies, scripts, run/test commands, and documentation evidence.
    """
    records: List[EvidenceRecord] = []
    lines = content.splitlines()
    file_name = rel_path.split("/")[-1].lower()

    # 1. Documentation files (README, CONTRIBUTING, LICENSE, docs/*.md)
    if any(k in file_name for k in ["readme", "contributing", "license", "licence"]) or rel_path.startswith("docs/"):
        records.append(
            EvidenceRecord(
                relative_path=rel_path,
                evidence_type=EvidenceType.DOCUMENTATION,
                description=f"Documentation file ({file_name})",
                start_line=1,
                end_line=min(10, len(lines)),
                snippet="\n".join(lines[:10]),
                metadata={"file_name": file_name},
            )
        )

        # Scan documentation lines for documented run and test commands
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Test commands
            for pat in TEST_CMD_PATTERNS:
                m = pat.search(stripped)
                if m:
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.TEST_COMMAND,
                            description=f"Documented test command: {m.group(0).strip()}",
                            start_line=idx,
                            end_line=idx,
                            snippet=stripped,
                            metadata={"command": m.group(0).strip(), "source": "docs"},
                        )
                    )
                    break
            # Run commands
            for pat in RUN_CMD_PATTERNS:
                m = pat.search(stripped)
                if m:
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=EvidenceType.RUN_COMMAND,
                            description=f"Documented run command: {m.group(0).strip()}",
                            start_line=idx,
                            end_line=idx,
                            snippet=stripped,
                            metadata={"command": m.group(0).strip(), "source": "docs"},
                        )
                    )
                    break

    # 2. Package Manifests: package.json
    if file_name == "package.json":
        records.append(
            EvidenceRecord(
                relative_path=rel_path,
                evidence_type=EvidenceType.MANIFEST,
                description="Node.js package manifest (package.json)",
                start_line=1,
                end_line=min(len(lines), 30),
                snippet="\n".join(lines[:30]),
            )
        )
        try:
            data = json.loads(content)
            scripts = data.get("scripts", {})
            for script_name, cmd in scripts.items():
                ev_type = EvidenceType.TEST_COMMAND if "test" in script_name.lower() else EvidenceType.RUN_COMMAND
                records.append(
                    EvidenceRecord(
                        relative_path=rel_path,
                        evidence_type=ev_type,
                        description=f"npm script '{script_name}': {cmd}",
                        start_line=1,
                        end_line=min(len(lines), 40),
                        snippet=f'"{script_name}": "{cmd}"',
                        metadata={"script_name": script_name, "command": cmd, "source": "package.json"},
                    )
                )
        except Exception:
            pass

    # 3. Python manifests: pyproject.toml, requirements.txt, setup.py
    elif file_name in {"pyproject.toml", "requirements.txt", "setup.py", "pipfile"}:
        records.append(
            EvidenceRecord(
                relative_path=rel_path,
                evidence_type=EvidenceType.MANIFEST,
                description=f"Python project manifest ({file_name})",
                start_line=1,
                end_line=min(len(lines), 35),
                snippet="\n".join(lines[:35]),
                metadata={"manifest_type": "python"},
            )
        )

    # 4. Makefiles, Dockerfiles, and CI/CD configs
    elif file_name in {"makefile", "dockerfile", "docker-compose.yml", "docker-compose.yaml"} or ".github/workflows" in rel_path:
        records.append(
            EvidenceRecord(
                relative_path=rel_path,
                evidence_type=EvidenceType.CONFIG,
                description=f"Project workflow/build config: {file_name}",
                start_line=1,
                end_line=min(len(lines), 20),
                snippet="\n".join(lines[:20]),
            )
        )
        # Parse Makefile targets
        if file_name == "makefile":
            for idx, line in enumerate(lines, start=1):
                if re.match(r"^[a-zA-Z0-9_\-]+:", line):
                    target = line.split(":")[0].strip()
                    ev_type = EvidenceType.TEST_COMMAND if "test" in target else EvidenceType.RUN_COMMAND
                    records.append(
                        EvidenceRecord(
                            relative_path=rel_path,
                            evidence_type=ev_type,
                            description=f"Makefile target: make {target}",
                            start_line=idx,
                            end_line=idx,
                            snippet=line.strip(),
                            metadata={"command": f"make {target}", "source": "makefile"},
                        )
                    )

    return records
