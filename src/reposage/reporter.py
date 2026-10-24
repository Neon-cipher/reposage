import json
import re
import time
from typing import Dict, Any, List, Optional
from reposage.models import (
    RepoFacts,
    AnalysisResult,
    Finding,
    FindingCategory,
    Opportunity,
    CodeCitation,
)
from reposage.scanner import scan_repository
from reposage.analyzers.python_ast import analyze_python_file
from reposage.analyzers.generic import analyze_generic_file, extract_package_dependencies
from reposage.ollama_client import OllamaClient
from reposage.prompts import SYSTEM_PROMPT, build_analysis_prompt


def analyze_repository_pipeline(
    repo_path: str,
    ollama_client: OllamaClient,
    model_name: str = "qwen2.5:latest",
) -> AnalysisResult:
    """
    Complete analysis pipeline:
    1. Deterministic repository scan (filesystem, sizes, ignore lists).
    2. Static code analysis (AST parsing for Python, regex for JS/TS, TODO extractor).
    3. Grounded Ollama inference (architecture synthesis & opportunity generation).
    4. Validation and unification of deterministic facts with AI findings.
    """
    start_time = time.time()

    # Step 1: Scan repository
    facts, file_contents = scan_repository(repo_path)

    # Step 2: Deterministic static analysis
    for rel_path, content in file_contents.items():
        # Dependencies from config files
        if rel_path.split("/")[-1].lower() in {"package.json", "requirements.txt", "pyproject.toml"}:
            extracted_deps = extract_package_dependencies(rel_path, content)
            facts.dependencies.extend(extracted_deps)

        # Analyze Python files with AST
        if rel_path.endswith(".py"):
            eps, syms, todos = analyze_python_file(rel_path, content)
            facts.entrypoints.extend(eps)
            facts.todos.extend(todos)
            if syms:
                facts.symbols[rel_path] = syms

        # Analyze JS/TS and generic files
        elif rel_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            eps, syms, todos = analyze_generic_file(rel_path, content)
            facts.entrypoints.extend(eps)
            facts.todos.extend(todos)
            if syms:
                facts.symbols[rel_path] = syms
        else:
            # Check for TODOs in generic text/source files
            _, _, todos = analyze_generic_file(rel_path, content)
            facts.todos.extend(todos)

    # Deduplicate dependencies
    facts.dependencies = sorted(list(set(facts.dependencies)))

    # Step 3: Build grounded sample set for Ollama prompt
    # Select critical files: README, config files, entrypoints, and high-symbol files
    sample_files: Dict[str, str] = {}
    if facts.readme_path and facts.readme_path in file_contents:
        sample_files[facts.readme_path] = file_contents[facts.readme_path]

    for cfg in facts.config_files:
        if cfg in file_contents and len(sample_files) < 6:
            sample_files[cfg] = file_contents[cfg]

    for ep in facts.entrypoints:
        if ep.file_path in file_contents and ep.file_path not in sample_files and len(sample_files) < 10:
            sample_files[ep.file_path] = file_contents[ep.file_path]

    # Fill remaining slots with top source files
    for path, content in file_contents.items():
        if len(sample_files) >= 10:
            break
        if path not in sample_files and path.endswith((".py", ".ts", ".js")):
            sample_files[path] = content

    # Step 4: Perform Ollama inference
    prompt = build_analysis_prompt(facts, sample_files)

    raw_response = ollama_client.generate(
        model=model_name,
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.1,
    )

    # Step 5: Clean and parse JSON response
    parsed_json = _clean_and_parse_json(raw_response)

    findings: List[Finding] = []
    opportunities: List[Opportunity] = []

    # Inject guaranteed deterministic facts as verified findings
    findings.append(
        Finding(
            category=FindingCategory.FACT,
            title="Repository Structure & Size",
            description=f"Scanned {facts.total_files_scanned} files comprising {facts.total_lines} total lines of code.",
            confidence=1.0,
            tags=["structure"],
        )
    )

    if facts.has_readme:
        findings.append(
            Finding(
                category=FindingCategory.FACT,
                title="README Detected",
                description=f"Found repository documentation in '{facts.readme_path}'.",
                citation=CodeCitation(file_path=facts.readme_path or "", start_line=1, end_line=1),
                confidence=1.0,
                tags=["documentation"],
            )
        )
    else:
        findings.append(
            Finding(
                category=FindingCategory.FACT,
                title="Missing Documentation",
                description="No README file detected in the repository root.",
                confidence=1.0,
                tags=["documentation", "opportunity"],
            )
        )

    if facts.has_license:
        findings.append(
            Finding(
                category=FindingCategory.FACT,
                title="Open Source License",
                description=f"Identified open-source license file: {facts.license_type}",
                confidence=1.0,
                tags=["governance"],
            )
        )
    else:
        findings.append(
            Finding(
                category=FindingCategory.FACT,
                title="Missing License",
                description="No LICENSE file detected. Potential governance concern for open-source contributions.",
                confidence=1.0,
                tags=["governance", "risk"],
            )
        )

    # Process AI findings safely
    if parsed_json and "findings" in parsed_json:
        for f in parsed_json["findings"]:
            cat_str = str(f.get("category", "inference")).lower()
            if "fact" in cat_str:
                category = FindingCategory.FACT
            elif "unknown" in cat_str:
                category = FindingCategory.UNKNOWN
            else:
                category = FindingCategory.INFERENCE

            citation = None
            fpath = f.get("file_path")
            sline = f.get("start_line")
            eline = f.get("end_line")
            if fpath:
                citation = CodeCitation(
                    file_path=str(fpath),
                    start_line=int(sline) if sline is not None else 1,
                    end_line=int(eline) if eline is not None else (int(sline) if sline is not None else 1),
                )

            findings.append(
                Finding(
                    category=category,
                    title=str(f.get("title", "Observation")),
                    description=str(f.get("description", "")),
                    citation=citation,
                    confidence=float(f.get("confidence", 0.8)),
                )
            )

    # Process AI opportunities
    if parsed_json and "opportunities" in parsed_json:
        for opp in parsed_json["opportunities"]:
            opportunities.append(
                Opportunity(
                    title=str(opp.get("title", "Hacktoberfest Contribution Task")),
                    difficulty=str(opp.get("difficulty", "Good First Issue (Beginner)")),
                    rationale=str(opp.get("rationale", "")),
                    file_path=str(opp.get("file_path", "")),
                    line_number=opp.get("line_number"),
                    action_items=[str(a) for a in opp.get("action_items", [])],
                    pr_template_suggestion=opp.get("pr_template_suggestion"),
                )
            )

    # If AI opportunities were sparse, supplement with concrete TODO items as beginner tasks
    if len(opportunities) < 2 and facts.todos:
        for td in facts.todos[:3]:
            opportunities.append(
                Opportunity(
                    title=f"Address {td.tag}: {td.text[:40]}...",
                    difficulty="Good First Issue (Beginner)",
                    rationale=f"Found explicit {td.tag} comment in source code.",
                    file_path=td.file_path,
                    line_number=td.line_number,
                    action_items=[
                        f"Open {td.file_path} at line {td.line_number}",
                        f"Review the comment '{td.text}' and resolve the stated request",
                        "Verify code runs without regressions and submit PR",
                    ],
                    pr_template_suggestion=f"fix: resolve {td.tag.lower()} in {td.file_path}",
                )
            )

    duration = time.time() - start_time
    summary_overview = parsed_json.get("summary_overview", "Repository analysis complete.") if parsed_json else "Repository analyzed."
    arch_overview = parsed_json.get("architecture_overview", "Structure inspected deterministically.") if parsed_json else "Structure analyzed."

    return AnalysisResult(
        facts=facts,
        summary_overview=summary_overview,
        architecture_overview=arch_overview,
        findings=findings,
        opportunities=opportunities,
        model_name=model_name,
        analysis_duration_sec=duration,
    )


def _clean_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Clean markdown fence wrapping and extract valid JSON."""
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    # Strip markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Regex search for first { and last }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                pass
    return None
