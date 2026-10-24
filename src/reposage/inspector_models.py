from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum


class EvidenceType(str, Enum):
    DOCUMENTATION = "documentation"
    MANIFEST = "manifest"
    ENTRYPOINT = "entrypoint"
    IMPORT = "import"
    TEST = "test"
    CONFIG = "config"
    RUN_COMMAND = "run_command"
    TEST_COMMAND = "test_command"
    CODE_SYMBOL = "code_symbol"
    TODO = "todo"


@dataclass
class EvidenceRecord:
    """An atomic piece of grounded evidence extracted from actual file contents."""
    relative_path: str
    evidence_type: EvidenceType
    description: str
    start_line: int
    end_line: int
    snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format_citation(self) -> str:
        if self.start_line == self.end_line:
            return f"{self.relative_path}:L{self.start_line}"
        return f"{self.relative_path}:L{self.start_line}-L{self.end_line}"


@dataclass
class InspectionLimits:
    """Configurable limits for deterministic scanning to prevent exhaustion and handle large repos."""
    max_files: int = 1_000
    max_file_size_bytes: int = 300_000  # 300 KB limit per file
    max_total_bytes: int = 15_000_000   # 15 MB total scanned text limit
    max_evidence_snippets_per_file: int = 100


@dataclass
class DeterministicSummary:
    """Summary of deterministic inspection output without any AI interpretation."""
    root_path: str
    total_files_scanned: int
    total_lines: int
    languages_by_count: Dict[str, int] = field(default_factory=dict)
    languages_by_lines: Dict[str, int] = field(default_factory=dict)
    important_manifests: List[str] = field(default_factory=list)
    candidate_entrypoints: List[str] = field(default_factory=list)
    test_directories: List[str] = field(default_factory=list)
    documentation_files: List[str] = field(default_factory=list)
    has_readme: bool = False
    has_contributing: bool = False
    has_license: bool = False
    documentation_coverage_score: float = 0.0  # 0.0 to 1.0 heuristic
    candidate_run_commands: List[str] = field(default_factory=list)
    candidate_test_commands: List[str] = field(default_factory=list)
    skipped_reasons: Dict[str, int] = field(default_factory=dict)


@dataclass
class InspectionResult:
    """Complete output of deterministic repository inspection."""
    summary: DeterministicSummary
    evidence_index: List[EvidenceRecord] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)
    excluded_files_count: int = 0
    skipped_items: List[str] = field(default_factory=list)
