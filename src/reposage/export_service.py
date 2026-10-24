import json
from typing import Dict, Any, List
from reposage.inspector_models import InspectionResult
from reposage.ai.ai_models import AIAnalysisReport, FindingNature


def export_report_to_json(
    inspection: InspectionResult,
    ai_report: AIAnalysisReport,
) -> str:
    """Export the complete deterministic and AI analysis report as structured JSON."""
    data: Dict[str, Any] = {
        "metadata": {
            "root_path": inspection.summary.root_path,
            "model_name": ai_report.model_name,
            "endpoint": ai_report.endpoint,
            "total_files_scanned": inspection.summary.total_files_scanned,
            "total_lines": inspection.summary.total_lines,
            "languages": inspection.summary.languages_by_count,
            "total_evidence_provided": ai_report.total_evidence_provided,
            "total_evidence_cited": ai_report.total_evidence_cited,
            "rejected_evidence_ids": ai_report.rejected_evidence_ids,
        },
        "deterministic_summary": {
            "has_readme": inspection.summary.has_readme,
            "has_license": inspection.summary.has_license,
            "has_contributing": inspection.summary.has_contributing,
            "documentation_coverage_score": inspection.summary.documentation_coverage_score,
            "manifests": inspection.summary.important_manifests,
            "candidate_entrypoints": inspection.summary.candidate_entrypoints,
            "test_directories": inspection.summary.test_directories,
            "run_commands": inspection.summary.candidate_run_commands,
            "test_commands": inspection.summary.candidate_test_commands,
            "skipped_reasons": inspection.summary.skipped_reasons,
        },
        "project_overview": {
            "purpose": ai_report.overview.purpose,
            "main_components": ai_report.overview.main_components,
            "likely_audience": ai_report.overview.likely_audience,
            "key_technologies": ai_report.overview.key_technologies,
            "unknowns": ai_report.overview.unknowns,
            "findings": [
                {
                    "nature": f.nature.value,
                    "statement": f.statement,
                    "evidence_ids": f.evidence_ids,
                    "is_flagged": f.is_flagged,
                    "flag_reason": f.flag_reason,
                    "citations": [
                        {
                            "evidence_id": c.evidence_id,
                            "file_path": c.file_path,
                            "line_range": c.line_range,
                            "is_valid": c.is_valid,
                            "flag_reason": c.flag_reason,
                        }
                        for c in f.citations
                    ],
                }
                for f in ai_report.overview.findings
            ],
        },
        "architecture_explanation": {
            "system_overview": ai_report.architecture.system_overview,
            "unknowns": ai_report.architecture.unknowns,
            "modules": [
                {
                    "name": m.name,
                    "file_path": m.file_path,
                    "responsibilities": m.responsibilities,
                    "verified_imports": m.verified_imports,
                    "inferred_runtime_relationships": m.inferred_runtime_relationships,
                    "evidence_ids": m.evidence_ids,
                }
                for m in ai_report.architecture.modules
            ],
            "findings": [
                {
                    "nature": f.nature.value,
                    "statement": f.statement,
                    "evidence_ids": f.evidence_ids,
                    "is_flagged": f.is_flagged,
                    "flag_reason": f.flag_reason,
                }
                for f in ai_report.architecture.findings
            ],
        },
        "contribution_roadmap": {
            "general_guidance": ai_report.roadmap.general_guidance,
            "unknowns": ai_report.roadmap.unknowns,
            "tasks": [
                {
                    "title": t.title,
                    "is_speculative": t.is_speculative,
                    "rationale": t.rationale,
                    "relevant_files": t.relevant_files,
                    "prerequisites": t.prerequisites,
                    "validation_suggestions": t.validation_suggestions,
                    "evidence_ids": t.evidence_ids,
                    "citations": [
                        {
                            "evidence_id": c.evidence_id,
                            "file_path": c.file_path,
                            "line_range": c.line_range,
                            "is_valid": c.is_valid,
                        }
                        for c in t.citations
                    ],
                }
                for t in ai_report.roadmap.tasks
            ],
            "findings": [
                {
                    "nature": f.nature.value,
                    "statement": f.statement,
                    "evidence_ids": f.evidence_ids,
                    "is_flagged": f.is_flagged,
                }
                for f in ai_report.roadmap.findings
            ],
        },
    }
    return json.dumps(data, indent=2)


def export_report_to_markdown(
    inspection: InspectionResult,
    ai_report: AIAnalysisReport,
) -> str:
    """Export the validated report as clean, GitHub-flavored markdown."""
    lines: List[str] = []

    lines.append(f"# RepoSage Analysis Report: `{inspection.summary.root_path}`\n")
    lines.append(f"- **Inference Model**: `{ai_report.model_name}` ({ai_report.endpoint})")
    lines.append(f"- **Scanned Files**: {inspection.summary.total_files_scanned} ({inspection.summary.total_lines:,} lines)")
    lines.append(f"- **Documentation Coverage**: {int(inspection.summary.documentation_coverage_score * 100)}%")
    lines.append(f"- **Evidence Cited / Provided**: {ai_report.total_evidence_cited} / {ai_report.total_evidence_provided}")
    if ai_report.rejected_evidence_ids:
        lines.append(f"- **Rejected Evidence IDs**: `{', '.join(ai_report.rejected_evidence_ids)}`")
    lines.append("\n---\n")

    # 1. Project Overview
    lines.append("## 1. Project Overview\n")
    lines.append(f"**Purpose**: {ai_report.overview.purpose}\n")
    lines.append(f"**Likely Audience**: {ai_report.overview.likely_audience}\n")

    lines.append("### Key Technologies")
    for tech in ai_report.overview.key_technologies:
        lines.append(f"- {tech}")

    lines.append("\n### Main Components")
    for comp in ai_report.overview.main_components:
        lines.append(f"- {comp}")

    if ai_report.overview.unknowns:
        lines.append("\n### Declared Unknowns")
        for unk in ai_report.overview.unknowns:
            lines.append(f"- ⚠️ *{unk}*")

    lines.append("\n---\n")

    # 2. Architecture Explanation
    lines.append("## 2. Architecture & Module Structure\n")
    lines.append(f"{ai_report.architecture.system_overview}\n")

    if ai_report.architecture.modules:
        lines.append("### Evidenced Modules")
        for m in ai_report.architecture.modules:
            lines.append(f"#### `{m.name}` (`{m.file_path}`)")
            lines.append(f"- **Responsibilities**: {m.responsibilities}")
            if m.verified_imports:
                lines.append(f"- **Verified Imports**: {', '.join(f'`{i}`' for i in m.verified_imports)}")
            if m.inferred_runtime_relationships:
                lines.append(f"- **Inferred Runtime Relationships**: {', '.join(f'*{r}*' for r in m.inferred_runtime_relationships)}")
            if m.evidence_ids:
                lines.append(f"- **Evidence Citations**: {', '.join(f'`{eid}`' for eid in m.evidence_ids)}")
            lines.append("")

    if ai_report.architecture.unknowns:
        lines.append("### Architecture Unknowns")
        for unk in ai_report.architecture.unknowns:
            lines.append(f"- ⚠️ *{unk}*")

    lines.append("\n---\n")

    # 3. Contribution Roadmap
    lines.append("## 3. Beginner-Friendly Contribution Roadmap\n")
    if ai_report.roadmap.general_guidance:
        lines.append(f"{ai_report.roadmap.general_guidance}\n")

    for idx, task in enumerate(ai_report.roadmap.tasks, start=1):
        spec_label = " (Speculative)" if task.is_speculative else " (Evidenced)"
        lines.append(f"### Task {idx}: {task.title}{spec_label}\n")
        lines.append(f"- **Rationale**: {task.rationale}")
        lines.append(f"- **Target Files**: {', '.join(f'`{f}`' for f in task.relevant_files)}")
        if task.prerequisites:
            lines.append(f"- **Prerequisites**: {', '.join(task.prerequisites)}")
        if task.validation_suggestions:
            lines.append("- **Validation Steps**:")
            for val in task.validation_suggestions:
                lines.append(f"  - {val}")
        if task.citations:
            lines.append(f"- **Citations**: {', '.join(f'`{c.file_path}:{c.line_range}`' for c in task.citations)}")
        lines.append("")

    lines.append("\n---\n")

    # 4. Evidence Citations
    lines.append("## 4. Cited Evidence Excerpts\n")
    # Collect all citations across overview, architecture, and roadmap
    all_citations: List[Dict[str, Any]] = []
    for f in ai_report.overview.findings:
        for c in f.citations:
            all_citations.append({"id": c.evidence_id, "file": c.file_path, "range": c.line_range, "stmt": f.statement})
    for t in ai_report.roadmap.tasks:
        for c in t.citations:
            all_citations.append({"id": c.evidence_id, "file": c.file_path, "range": c.line_range, "stmt": t.title})

    seen = set()
    for item in all_citations:
        key = (item["id"], item["file"])
        if key not in seen:
            seen.add(key)
            lines.append(f"- **`{item['id']}`** -> `{item['file']}` ({item['range']}): *{item['stmt']}*")

    return "\n".join(lines)
