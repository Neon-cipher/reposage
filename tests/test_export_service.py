import json
import pytest
from pathlib import Path
from reposage.inspector_models import (
    InspectionResult,
    DeterministicSummary,
    EvidenceRecord,
    EvidenceType,
)
from reposage.ai.ai_models import (
    AIAnalysisReport,
    ProjectOverview,
    ArchitectureExplanation,
    ContributionRoadmap,
    ContributionTask,
    GroundedFinding,
    FindingNature,
    EvidenceCitation,
)
from reposage.export_service import export_report_to_json, export_report_to_markdown


@pytest.fixture
def sample_analysis() -> tuple[InspectionResult, AIAnalysisReport]:
    summary = DeterministicSummary(
        root_path="/mock/repo",
        total_files_scanned=2,
        total_lines=50,
        languages_by_count={"Python": 2},
        documentation_coverage_score=0.8,
        important_manifests=["pyproject.toml"],
        candidate_entrypoints=["main.py:L1"],
        candidate_run_commands=["python main.py"],
        candidate_test_commands=["pytest"],
        skipped_reasons={"Secret extension: .pem": 1},
    )
    ev = EvidenceRecord(
        relative_path="main.py",
        evidence_type=EvidenceType.ENTRYPOINT,
        description="Entrypoint main",
        start_line=1,
        end_line=5,
        snippet="def main(): pass",
    )
    inspection = InspectionResult(
        summary=summary,
        evidence_index=[ev],
        file_contents={"main.py": "def main(): pass"},
        excluded_files_count=1,
    )

    overview = ProjectOverview(
        purpose="A lightweight testing repo",
        main_components=["Core parser"],
        likely_audience="Open source developers",
        key_technologies=["Python", "Streamlit"],
        findings=[
            GroundedFinding(
                nature=FindingNature.OBSERVATION,
                statement="Verified entry point in main.py",
                evidence_ids=["ev_1"],
                citations=[EvidenceCitation(evidence_id="ev_1", file_path="main.py", line_range="L1-L5")],
            )
        ],
        unknowns=["No CI workflow found"],
    )

    architecture = ArchitectureExplanation(
        system_overview="Monolithic script layout",
        modules=[],
        findings=[],
        unknowns=[],
    )

    roadmap = ContributionRoadmap(
        general_guidance="Focus on test coverage",
        tasks=[
            ContributionTask(
                title="Add unit tests for main()",
                is_speculative=False,
                rationale="No existing tests for main()",
                relevant_files=["main.py"],
                prerequisites=["pytest"],
                validation_suggestions=["pytest tests/"],
                evidence_ids=["ev_1"],
                citations=[EvidenceCitation(evidence_id="ev_1", file_path="main.py", line_range="L1-L5")],
            )
        ],
        findings=[],
        unknowns=[],
    )

    report = AIAnalysisReport(
        model_name="qwen2.5:latest",
        endpoint="http://localhost:11434",
        overview=overview,
        architecture=architecture,
        roadmap=roadmap,
        total_evidence_provided=1,
        total_evidence_cited=1,
        rejected_evidence_ids=[],
    )

    return inspection, report


def test_export_report_to_json(sample_analysis):
    inspection, report = sample_analysis
    exported_json = export_report_to_json(inspection, report)

    data = json.loads(exported_json)
    assert data["metadata"]["root_path"] == "/mock/repo"
    assert data["metadata"]["model_name"] == "qwen2.5:latest"
    assert "analysis_timestamp_utc" in data["metadata"]
    assert "PROVISIONAL NOTICE" in data["metadata"]["disclaimer"]
    assert len(data["metadata"]["limitations"]) > 0
    assert data["project_overview"]["purpose"] == "A lightweight testing repo"
    assert len(data["contribution_roadmap"]["tasks"]) == 1
    assert data["contribution_roadmap"]["tasks"][0]["title"] == "Add unit tests for main()"


def test_export_report_to_markdown(sample_analysis):
    inspection, report = sample_analysis
    exported_md = export_report_to_markdown(inspection, report)

    assert "# RepoSage Analysis Report: `/mock/repo`" in exported_md
    assert "PROVISIONAL NOTICE" in exported_md
    assert "Analysis Timestamp" in exported_md
    assert "Known Analysis Limitations" in exported_md
    assert "**Purpose**: A lightweight testing repo" in exported_md
    assert "### Task 1: Add unit tests for main() (Evidenced)" in exported_md
    assert "main.py" in exported_md
    assert "qwen2.5:latest" in exported_md
