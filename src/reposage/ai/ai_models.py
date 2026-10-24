from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class FindingNature(str, Enum):
    OBSERVATION = "observation"  # Directly verified from evidence
    INFERENCE = "inference"      # Deductions / reasoning
    UNKNOWN = "unknown"          # Explicitly unverified / unknown


@dataclass
class EvidenceCitation:
    """Citation linking back to a grounded EvidenceRecord."""
    evidence_id: str
    file_path: str
    line_range: str
    is_valid: bool = True
    flag_reason: Optional[str] = None


@dataclass
class GroundedFinding:
    """A single finding strictly citing one or more valid evidence IDs."""
    nature: FindingNature
    statement: str
    evidence_ids: List[str] = field(default_factory=list)
    citations: List[EvidenceCitation] = field(default_factory=list)
    is_flagged: bool = False
    flag_reason: Optional[str] = None


@dataclass
class ProjectOverview:
    """Operation A: Project Purpose, Main Components, Audience, and Technologies."""
    purpose: str
    main_components: List[str]
    likely_audience: str
    key_technologies: List[str]
    findings: List[GroundedFinding] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)


@dataclass
class ArchitectureModule:
    name: str
    file_path: str
    responsibilities: str
    verified_imports: List[str]
    inferred_runtime_relationships: List[str]
    evidence_ids: List[str] = field(default_factory=list)


@dataclass
class ArchitectureExplanation:
    """Operation B: Module Responsibilities and Import Relationships."""
    system_overview: str
    modules: List[ArchitectureModule] = field(default_factory=list)
    findings: List[GroundedFinding] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)


@dataclass
class ContributionTask:
    title: str
    is_speculative: bool
    rationale: str
    relevant_files: List[str]
    prerequisites: List[str]
    validation_suggestions: List[str]
    evidence_ids: List[str] = field(default_factory=list)
    citations: List[EvidenceCitation] = field(default_factory=list)


@dataclass
class ContributionRoadmap:
    """Operation C: Three Beginner-Friendly Tasks with Rationale and Validation."""
    tasks: List[ContributionTask] = field(default_factory=list)
    general_guidance: str = ""
    findings: List[GroundedFinding] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)


@dataclass
class AIAnalysisReport:
    """Unified result of all three AI analysis operations."""
    model_name: str
    endpoint: str
    overview: ProjectOverview
    architecture: ArchitectureExplanation
    roadmap: ContributionRoadmap
    total_evidence_provided: int
    total_evidence_cited: int
    rejected_evidence_ids: List[str] = field(default_factory=list)
    raw_response_cached: Optional[str] = None
