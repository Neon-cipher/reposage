from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class FindingCategory(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"
    UNKNOWN = "unknown"


@dataclass
class CodeCitation:
    """Exact file and line range citation for verifiable findings."""
    file_path: str
    start_line: int
    end_line: int
    snippet: Optional[str] = None

    def format_citation(self) -> str:
        if self.start_line == self.end_line:
            return f"{self.file_path}:L{self.start_line}"
        return f"{self.file_path}:L{self.start_line}-L{self.end_line}"


@dataclass
class TodoItem:
    """Discovered actionable comment with location."""
    file_path: str
    line_number: int
    tag: str  # TODO, FIXME, HACK, XXX
    text: str


@dataclass
class RepoFacts:
    """Deterministic, verifiable facts extracted strictly without LLM."""
    root_path: str
    total_files_scanned: int
    total_lines: int
    language_counts: Dict[str, int] = field(default_factory=dict)
    language_lines: Dict[str, int] = field(default_factory=dict)
    entrypoints: List[CodeCitation] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    has_readme: bool = False
    readme_path: Optional[str] = None
    has_contributing: bool = False
    contributing_path: Optional[str] = None
    has_license: bool = False
    license_type: Optional[str] = None
    has_tests: bool = False
    test_files: List[str] = field(default_factory=list)
    todos: List[TodoItem] = field(default_factory=list)
    symbols: Dict[str, List[str]] = field(default_factory=dict)  # file -> list of defined classes/functions
    config_files: List[str] = field(default_factory=list)
    skipped_items: List[str] = field(default_factory=list)


@dataclass
class Finding:
    """A single finding strictly categorized as Fact, Inference, or Unknown."""
    category: FindingCategory
    title: str
    description: str
    citation: Optional[CodeCitation] = None
    confidence: float = 1.0  # 1.0 for facts, 0.0-0.9 for inferences
    tags: List[str] = field(default_factory=list)


@dataclass
class Opportunity:
    """A beginner-friendly Hacktoberfest contribution opportunity."""
    title: str
    difficulty: str  # "Good First Issue (Beginner)", "Junior / Intermediate"
    rationale: str
    file_path: str
    line_number: Optional[int] = None
    action_items: List[str] = field(default_factory=list)
    pr_template_suggestion: Optional[str] = None


@dataclass
class AnalysisResult:
    """Complete analysis output combining deterministic facts and grounded inferences."""
    facts: RepoFacts
    summary_overview: str
    architecture_overview: str
    findings: List[Finding] = field(default_factory=list)
    opportunities: List[Opportunity] = field(default_factory=list)
    model_name: str = "ollama"
    analysis_duration_sec: float = 0.0
