import json
import re
from typing import Dict, Any, List, Tuple, Set, Optional

from reposage.inspector_models import EvidenceRecord, InspectionResult
from reposage.ai.ai_models import (
    FindingNature,
    EvidenceCitation,
    GroundedFinding,
    ProjectOverview,
    ArchitectureModule,
    ArchitectureExplanation,
    ContributionTask,
    ContributionRoadmap,
    AIAnalysisReport,
)


class SchemaValidationError(Exception):
    """Raised when model response fails schema validation."""
    pass


def parse_and_clean_json(raw_text: str) -> Dict[str, Any]:
    """Extract and parse valid JSON from raw model text with fallback cleaning."""
    if not raw_text or not raw_text.strip():
        raise SchemaValidationError("Model returned empty response.")

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    # Clean potential model artifacts like '"nature": "observation" or "inference"'
    cleaned_pre = re.sub(r'("[^"]+")\s+or\s+"[^"]+"(?:\s+or\s+"[^"]+")*', r'\1', cleaned)

    try:
        data = json.loads(cleaned_pre)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Regex search for first { and last }
    s = cleaned_pre.find("{")
    e = cleaned_pre.rfind("}")
    if s != -1 and e != -1 and e > s:
        candidate = cleaned_pre[s : e + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            # Try removing trailing commas
            candidate_no_commas = re.sub(r',\s*([}\]])', r'\1', candidate)
            try:
                data = json.loads(candidate_no_commas)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

    raise SchemaValidationError("Failed to parse valid JSON from model output.")


def validate_and_resolve_citations(
    claimed_ids: List[str],
    evidence_map: Dict[str, EvidenceRecord],
    valid_file_paths: Set[str],
) -> Tuple[List[EvidenceCitation], bool, Optional[str]]:
    """
    Validate that claimed evidence IDs actually exist in the provided evidence index.
    Flags invalid or nonexistent IDs.
    Returns (citations, is_flagged, flag_reason).
    """
    citations: List[EvidenceCitation] = []
    is_flagged = False
    flag_reasons = []

    if not claimed_ids:
        # Factual statements require at least one citation
        return [], True, "No evidence IDs cited for factual claim"

    for eid in claimed_ids:
        if eid not in evidence_map:
            is_flagged = True
            flag_reasons.append(f"Cited nonexistent evidence ID: '{eid}'")
            citations.append(
                EvidenceCitation(
                    evidence_id=eid,
                    file_path="[UNKNOWN]",
                    line_range="[UNKNOWN]",
                    is_valid=False,
                    flag_reason="ID not found in evidence index",
                )
            )
        else:
            rec = evidence_map[eid]
            # Verify file path is in repository
            if rec.relative_path not in valid_file_paths:
                is_flagged = True
                flag_reasons.append(f"Cited file '{rec.relative_path}' is not an active repository path")
                citations.append(
                    EvidenceCitation(
                        evidence_id=eid,
                        file_path=rec.relative_path,
                        line_range=f"L{rec.start_line}-L{rec.end_line}",
                        is_valid=False,
                        flag_reason="Invalid repository file path",
                    )
                )
            else:
                citations.append(
                    EvidenceCitation(
                        evidence_id=eid,
                        file_path=rec.relative_path,
                        line_range=f"L{rec.start_line}-L{rec.end_line}",
                        is_valid=True,
                    )
                )

    combined_reason = "; ".join(flag_reasons) if flag_reasons else None
    return citations, is_flagged, combined_reason


def process_grounded_findings(
    raw_findings: List[Dict[str, Any]],
    evidence_map: Dict[str, EvidenceRecord],
    valid_file_paths: Set[str],
    all_cited_ids: Set[str],
    all_rejected_ids: Set[str],
) -> List[GroundedFinding]:
    """Parse raw findings, validate their citations against active evidence, and flag hallucinations."""
    processed: List[GroundedFinding] = []

    for item in raw_findings:
        statement = str(item.get("statement", "")).strip()
        if not statement:
            continue

        nature_str = str(item.get("nature", "inference")).lower()
        if "obs" in nature_str or "fact" in nature_str:
            nature = FindingNature.OBSERVATION
        elif "unk" in nature_str:
            nature = FindingNature.UNKNOWN
        else:
            nature = FindingNature.INFERENCE

        claimed_ids = [str(x).strip() for x in item.get("evidence_ids", []) if str(x).strip()]

        # Track IDs
        for cid in claimed_ids:
            if cid in evidence_map:
                all_cited_ids.add(cid)
            else:
                all_rejected_ids.add(cid)

        citations, is_flagged, flag_reason = validate_and_resolve_citations(
            claimed_ids, evidence_map, valid_file_paths
        )

        # Unknowns do not require citation flags
        if nature == FindingNature.UNKNOWN:
            is_flagged = False
            flag_reason = None

        processed.append(
            GroundedFinding(
                nature=nature,
                statement=statement,
                evidence_ids=claimed_ids,
                citations=citations,
                is_flagged=is_flagged,
                flag_reason=flag_reason,
            )
        )

    return processed


def build_validated_report(
    raw_data: Dict[str, Any],
    evidence_map: Dict[str, EvidenceRecord],
    inspection: InspectionResult,
    model_name: str,
    endpoint: str,
) -> AIAnalysisReport:
    """Validate JSON payload against required operations, build typed models, and resolve all evidence."""
    valid_file_paths = set(inspection.file_contents.keys())
    all_cited_ids: Set[str] = set()
    all_rejected_ids: Set[str] = set()

    # 1. Validate Operation A: Project Overview
    raw_overview = raw_data.get("project_overview")
    if not isinstance(raw_overview, dict):
        raise SchemaValidationError("Missing required 'project_overview' object in response.")

    purpose = str(raw_overview.get("purpose", "")).strip()
    if not purpose:
        raise SchemaValidationError("Project overview must contain non-empty 'purpose'.")

    main_components = [str(c) for c in raw_overview.get("main_components", [])]
    likely_audience = str(raw_overview.get("likely_audience", "Developers"))
    key_technologies = [str(t) for t in raw_overview.get("key_technologies", [])]
    overview_unknowns = [str(u) for u in raw_overview.get("unknowns", [])]

    overview_findings = process_grounded_findings(
        raw_overview.get("findings", []),
        evidence_map,
        valid_file_paths,
        all_cited_ids,
        all_rejected_ids,
    )

    overview = ProjectOverview(
        purpose=purpose,
        main_components=main_components,
        likely_audience=likely_audience,
        key_technologies=key_technologies,
        findings=overview_findings,
        unknowns=overview_unknowns,
    )

    # 2. Validate Operation B: Architecture Explanation
    raw_arch = raw_data.get("architecture_explanation")
    if not isinstance(raw_arch, dict):
        raise SchemaValidationError("Missing required 'architecture_explanation' object in response.")

    system_overview = str(raw_arch.get("system_overview", "")).strip()
    modules: List[ArchitectureModule] = []
    for mod in raw_arch.get("modules", []):
        m_name = str(mod.get("name", "Module"))
        m_path = str(mod.get("file_path", ""))
        m_resp = str(mod.get("responsibilities", ""))
        v_imports = [str(i) for i in mod.get("verified_imports", [])]
        inferred_rel = [str(r) for r in mod.get("inferred_runtime_relationships", [])]
        e_ids = [str(eid) for eid in mod.get("evidence_ids", [])]

        for eid in e_ids:
            if eid in evidence_map:
                all_cited_ids.add(eid)
            else:
                all_rejected_ids.add(eid)

        modules.append(
            ArchitectureModule(
                name=m_name,
                file_path=m_path,
                responsibilities=m_resp,
                verified_imports=v_imports,
                inferred_runtime_relationships=inferred_rel,
                evidence_ids=e_ids,
            )
        )

    arch_findings = process_grounded_findings(
        raw_arch.get("findings", []),
        evidence_map,
        valid_file_paths,
        all_cited_ids,
        all_rejected_ids,
    )
    arch_unknowns = [str(u) for u in raw_arch.get("unknowns", [])]

    architecture = ArchitectureExplanation(
        system_overview=system_overview,
        modules=modules,
        findings=arch_findings,
        unknowns=arch_unknowns,
    )

    # 3. Validate Operation C: Contribution Roadmap
    raw_roadmap = raw_data.get("contribution_roadmap")
    if not isinstance(raw_roadmap, dict):
        raise SchemaValidationError("Missing required 'contribution_roadmap' object in response.")

    general_guidance = str(raw_roadmap.get("general_guidance", ""))
    tasks: List[ContributionTask] = []
    raw_tasks = raw_roadmap.get("tasks", [])

    for t in raw_tasks:
        title = str(t.get("title", "Contribution Task"))
        is_speculative = bool(t.get("is_speculative", False))
        rationale = str(t.get("rationale", ""))
        relevant_files = [str(f) for f in t.get("relevant_files", [])]
        prereqs = [str(p) for p in t.get("prerequisites", [])]
        val_suggestions = [str(v) for v in t.get("validation_suggestions", [])]
        e_ids = [str(eid) for eid in t.get("evidence_ids", [])]

        citations, _, _ = validate_and_resolve_citations(e_ids, evidence_map, valid_file_paths)
        for eid in e_ids:
            if eid in evidence_map:
                all_cited_ids.add(eid)
            else:
                all_rejected_ids.add(eid)

        tasks.append(
            ContributionTask(
                title=title,
                is_speculative=is_speculative,
                rationale=rationale,
                relevant_files=relevant_files,
                prerequisites=prereqs,
                validation_suggestions=val_suggestions,
                evidence_ids=e_ids,
                citations=citations,
            )
        )

    roadmap_findings = process_grounded_findings(
        raw_roadmap.get("findings", []),
        evidence_map,
        valid_file_paths,
        all_cited_ids,
        all_rejected_ids,
    )
    roadmap_unknowns = [str(u) for u in raw_roadmap.get("unknowns", [])]

    roadmap = ContributionRoadmap(
        tasks=tasks,
        general_guidance=general_guidance,
        findings=roadmap_findings,
        unknowns=roadmap_unknowns,
    )

    return AIAnalysisReport(
        model_name=model_name,
        endpoint=endpoint,
        overview=overview,
        architecture=architecture,
        roadmap=roadmap,
        total_evidence_provided=len(evidence_map),
        total_evidence_cited=len(all_cited_ids),
        rejected_evidence_ids=sorted(list(all_rejected_ids)),
        raw_response_cached=json.dumps(raw_data, indent=2),
    )
