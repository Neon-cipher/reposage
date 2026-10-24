import os
from pathlib import Path
import streamlit as st

from reposage.inspector import inspect_repository, validate_repository_root
from reposage.inspector_models import InspectionLimits, InspectionResult, EvidenceType
from reposage.ai.ollama_client import (
    LocalOllamaClient,
    get_ollama_endpoint,
    get_configured_model,
    OllamaConfigurationError,
    OllamaConnectionError,
    OllamaInferenceError,
)
from reposage.ai.engine import AIAnalysisEngine
from reposage.ai.ai_models import AIAnalysisReport, FindingNature
from reposage.export_service import export_report_to_markdown, export_report_to_json

# Page configuration
st.set_page_config(
    page_title="RepoSage - Local AI Repository Analyst",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "inspection_result" not in st.session_state:
    st.session_state.inspection_result = None
if "ai_report" not in st.session_state:
    st.session_state.ai_report = None
if "analyzed_repo_path" not in st.session_state:
    st.session_state.analyzed_repo_path = ""
if "last_error" not in st.session_state:
    st.session_state.last_error = None
if "selected_evidence_id" not in st.session_state:
    st.session_state.selected_evidence_id = None

# Custom styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .badge-observation {
        background-color: #064e3b;
        color: #34d399;
        padding: 2px 7px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-inference {
        background-color: #451a03;
        color: #fbbf24;
        padding: 2px 7px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-unknown {
        background-color: #4c0519;
        color: #f87171;
        padding: 2px 7px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-speculative {
        background-color: #3b0764;
        color: #c084fc;
        padding: 2px 7px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .card-task {
        background: #1e2430;
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 6px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .card-task-spec {
        background: #1e2430;
        border: 1px solid #334155;
        border-left: 4px solid #c084fc;
        border-radius: 6px;
        padding: 14px;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar Configuration
with st.sidebar:
    st.title("🌿 RepoSage")
    st.caption("Deterministic Inspection & Local AI Repository Orientation")

    st.subheader("1. Local Ollama Settings")
    default_url = get_ollama_endpoint()
    default_model = get_configured_model()

    ollama_url = st.text_input("Ollama HTTP URL", value=default_url, help="OLLAMA_URL environment variable")
    ollama_model = st.text_input("Configured Model", value=default_model, help="OLLAMA_MODEL environment variable")

    client = LocalOllamaClient(base_url=ollama_url, model_name=ollama_model)

    # Status check
    try:
        conn_info = client.check_connection()
        installed = conn_info.get("installed_models", [])
        st.success(f"Connected to local Ollama ({len(installed)} models found)")
        
        # Verify specific model
        try:
            client.verify_model_installed()
            st.caption(f"Verified active model: `{ollama_model}`")
        except OllamaConfigurationError as ce:
            st.warning(str(ce))
    except OllamaConnectionError as e:
        st.error(f"Ollama Offline: {e}")

    st.markdown("---")
    st.subheader("2. Target Repository")
    current_cwd = str(Path(os.getcwd()).resolve())
    repo_input = st.text_input("Local Folder Path", value=current_cwd)

    st.markdown("---")
    st.subheader("3. Inspection Limits")
    max_files = st.number_input("Max Files Scanned", min_value=10, max_value=5000, value=1000, step=50)
    max_file_size_kb = st.number_input("Max File Size (KB)", min_value=10, max_value=2000, value=300, step=50)

    # Actions
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        run_inspection_btn = st.button("1. Static Scan", type="secondary", use_container_width=True)
    with c_btn2:
        run_ai_btn = st.button("2. Run AI", type="primary", use_container_width=True)

# Path validation helper
def get_validated_root(path_str: str):
    try:
        return validate_repository_root(path_str)
    except Exception as e:
        st.error(f"Invalid path: {e}")
        return None

# Trigger 1: Deterministic Static Scan
if run_inspection_btn:
    validated_path = get_validated_root(repo_input)
    if validated_path:
        limits = InspectionLimits(
            max_files=int(max_files),
            max_file_size_bytes=int(max_file_size_kb * 1024),
        )
        with st.spinner("Executing deterministic inspection without code execution..."):
            try:
                res = inspect_repository(str(validated_path), limits=limits)
                st.session_state.inspection_result = res
                st.session_state.analyzed_repo_path = str(validated_path)
                st.session_state.ai_report = None  # Reset AI report if repo re-inspected
                st.session_state.last_error = None
                st.success(f"Deterministic scan finished: {res.summary.total_files_scanned} files inventory ready.")
            except Exception as e:
                st.session_state.last_error = str(e)
                st.error(f"Inspection error: {e}")

# Trigger 2: Local AI Analysis
if run_ai_btn:
    validated_path = get_validated_root(repo_input)
    if validated_path:
        # If no inspection yet or path changed, run inspection first
        if not st.session_state.inspection_result or st.session_state.analyzed_repo_path != str(validated_path):
            limits = InspectionLimits(
                max_files=int(max_files),
                max_file_size_bytes=int(max_file_size_kb * 1024),
            )
            with st.spinner("Running preliminary static inspection..."):
                try:
                    st.session_state.inspection_result = inspect_repository(str(validated_path), limits=limits)
                    st.session_state.analyzed_repo_path = str(validated_path)
                except Exception as e:
                    st.error(f"Inspection error: {e}")

        # Now run AI analysis
        if st.session_state.inspection_result:
            engine = AIAnalysisEngine(ollama_client=client)
            with st.spinner(f"Querying local model '{ollama_model}' with grounded evidence..."):
                try:
                    report = engine.analyze(st.session_state.inspection_result)
                    st.session_state.ai_report = report
                    st.session_state.last_error = None
                    st.success(f"AI analysis completed: {report.total_evidence_cited} citations validated.")
                except Exception as e:
                    st.session_state.last_error = str(e)
                    st.error(f"AI Analysis Failed: {e}")

# Display Dashboard
st.header("RepoSage Repository Intelligence Dashboard")

inspection = st.session_state.inspection_result
ai_report = st.session_state.ai_report

if not inspection:
    st.info("👈 Enter a local repository folder path and click **1. Static Scan** or **2. Run AI** to inspect the repository.")
else:
    # Top KPI Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Files Scanned", inspection.summary.total_files_scanned)
    with m2:
        st.metric("Lines of Code", f"{inspection.summary.total_lines:,}")
    with m3:
        st.metric("Doc Coverage", f"{int(inspection.summary.documentation_coverage_score * 100)}%")
    with m4:
        st.metric("Excluded Files", inspection.excluded_files_count)
    with m5:
        ai_status = "✅ Completed" if ai_report else "⏳ Pending"
        st.metric("AI Analysis", ai_status)

    st.markdown("---")

    # Main Tab Navigation
    tab_overview, tab_arch, tab_roadmap, tab_evidence, tab_inventory, tab_export = st.tabs(
        [
            "📋 Overview",
            "🏛️ Architecture",
            "🎯 Contribution Roadmap",
            "🔍 Cited Evidence",
            "🛡️ Exclusions & Inventory",
            "💾 Export Report",
        ]
    )

    # ---------------- TAB 1: OVERVIEW ----------------
    with tab_overview:
        st.subheader("Project Overview & Grounded Facts")

        if not ai_report:
            st.info("Deterministic facts collected. Click **2. Run AI** to generate AI-powered overview and explanations.")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### Languages Detected")
                st.json(inspection.summary.languages_by_count)
            with col_b:
                st.markdown("#### Detected Manifests & Configs")
                for m in inspection.summary.important_manifests:
                    st.markdown(f"- `{m}`")
        else:
            st.markdown("#### Purpose")
            st.info(ai_report.overview.purpose)

            col_o1, col_o2 = st.columns(2)
            with col_o1:
                st.markdown("#### Likely Audience")
                st.write(ai_report.overview.likely_audience)

                st.markdown("#### Key Technologies")
                for tech in ai_report.overview.key_technologies:
                    st.markdown(f"- `{tech}`")

            with col_o2:
                st.markdown("#### Main Components")
                for comp in ai_report.overview.main_components:
                    st.markdown(f"- {comp}")

            if ai_report.overview.unknowns:
                st.markdown("#### Declared Unknowns")
                for unk in ai_report.overview.unknowns:
                    st.warning(f"**Unknown**: {unk}")

            st.markdown("#### Grounded Findings & Citations")
            for f in ai_report.overview.findings:
                nature_class = f"badge-{f.nature.value}"
                flag_text = f" ⚠️ **[{f.flag_reason}]**" if f.is_flagged else ""
                cit_text = " | Citations: " + ", ".join(f"`{c.evidence_id} ({c.file_path}:{c.line_range})`" for c in f.citations) if f.citations else ""
                st.markdown(
                    f"""
                    <div style="margin-bottom: 8px;">
                        <span class="{nature_class}">[{f.nature.value.upper()}]</span> {f.statement} {flag_text}
                        <br><small style="color: #94a3b8;">{cit_text}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ---------------- TAB 2: ARCHITECTURE ----------------
    with tab_arch:
        st.subheader("Architecture & Module Relationships")

        if not ai_report:
            st.info("Run AI analysis to generate verified module responsibilities and runtime relationships.")
            st.markdown("#### Candidate Entrypoints (Deterministic)")
            for ep in inspection.summary.candidate_entrypoints:
                st.markdown(f"- `{ep}`")
        else:
            st.markdown("#### System Overview")
            st.write(ai_report.architecture.system_overview)

            if ai_report.architecture.unknowns:
                for unk in ai_report.architecture.unknowns:
                    st.warning(f"**Architecture Unknown**: {unk}")

            st.markdown("#### Evidenced Modules")
            for mod in ai_report.architecture.modules:
                with st.expander(f"📦 Module: {mod.name} (`{mod.file_path}`)", expanded=True):
                    st.markdown(f"**Responsibilities**: {mod.responsibilities}")
                    
                    c_v, c_i = st.columns(2)
                    with c_v:
                        st.markdown("**Verified Imports:**")
                        if mod.verified_imports:
                            for imp in mod.verified_imports:
                                st.markdown(f"- `{imp}`")
                        else:
                            st.caption("None verified")
                    
                    with c_i:
                        st.markdown("**Inferred Runtime Relationships:**")
                        if mod.inferred_runtime_relationships:
                            for rel in mod.inferred_runtime_relationships:
                                st.markdown(f"- *{rel}*")
                        else:
                            st.caption("None inferred")

                    if mod.evidence_ids:
                        st.caption(f"Evidence IDs: {', '.join(f'`{eid}`' for eid in mod.evidence_ids)}")

    # ---------------- TAB 3: CONTRIBUTION ROADMAP ----------------
    with tab_roadmap:
        st.subheader("Beginner-Friendly Contribution Roadmap")

        if not ai_report:
            st.info("Run AI analysis to generate grounded contribution opportunities.")
            st.markdown("#### Discovered Code Tags (TODO / FIXME)")
            todos = [e for e in inspection.evidence_index if e.evidence_type == EvidenceType.TODO]
            if todos:
                for td in todos[:15]:
                    st.markdown(f"- **`{td.relative_path}:{td.start_line}`**: *{td.snippet}*")
            else:
                st.caption("No explicit TODO comments discovered.")
        else:
            if ai_report.roadmap.general_guidance:
                st.info(ai_report.roadmap.general_guidance)

            for idx, task in enumerate(ai_report.roadmap.tasks, start=1):
                card_class = "card-task-spec" if task.is_speculative else "card-task"
                badge = '<span class="badge-speculative">[SPECULATIVE]</span>' if task.is_speculative else '<span class="badge-observation">[EVIDENCED]</span>'

                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <h4>Task {idx}: {task.title} {badge}</h4>
                        <p><strong>Rationale:</strong> {task.rationale}</p>
                        <p><strong>Relevant Files:</strong> {', '.join(f'<code>{f}</code>' for f in task.relevant_files)}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c_p, c_v = st.columns(2)
                with c_p:
                    st.markdown("**Prerequisites:**")
                    for p in task.prerequisites:
                        st.markdown(f"- {p}")
                with c_v:
                    st.markdown("**Validation Suggestions:**")
                    for v in task.validation_suggestions:
                        st.markdown(f"- {v}")

                if task.citations:
                    st.caption("Citations: " + ", ".join(f"`{c.evidence_id}` ({c.file_path}:{c.line_range})" for c in task.citations))
                st.divider()

    # ---------------- TAB 4: EVIDENCE ----------------
    with tab_evidence:
        st.subheader("Repository Evidence Index & Snippets")
        st.caption("All factual findings and AI models are strictly bound to these actual file excerpts.")

        col_filter1, col_filter2 = st.columns([1, 2])
        with col_filter1:
            ev_types = ["All"] + [t.value for t in EvidenceType]
            sel_type = st.selectbox("Filter Evidence Type", ev_types)

        filtered_evidence = inspection.evidence_index
        if sel_type != "All":
            filtered_evidence = [e for e in inspection.evidence_index if e.evidence_type.value == sel_type]

        st.caption(f"Showing {len(filtered_evidence)} evidence records:")

        for ev in filtered_evidence[:100]:
            with st.expander(f"[{ev.evidence_type.value.upper()}] `{ev.format_citation()}` - {ev.description}"):
                st.markdown(f"**Path**: `{ev.relative_path}` (Lines {ev.start_line} to {ev.end_line})")
                st.code(ev.snippet, language="text")

    # ---------------- TAB 5: INVENTORY & EXCLUSIONS ----------------
    with tab_inventory:
        st.subheader("Deterministic Inventory & Safe Exclusion Report")
        col_inv1, col_inv2 = st.columns(2)

        with col_inv1:
            st.markdown("#### Scanned Eligible Files")
            for file_path in list(inspection.file_contents.keys())[:30]:
                st.markdown(f"- `{file_path}`")
            if len(inspection.file_contents) > 30:
                st.caption(f"... and {len(inspection.file_contents) - 30} more files.")

        with col_inv2:
            st.markdown("#### Excluded from Ingestion & Walk")
            st.markdown(f"- **Total Excluded**: {inspection.excluded_files_count}")
            st.markdown("##### Exclusion Breakdown:")
            st.json(inspection.summary.skipped_reasons)

            if inspection.skipped_items:
                with st.expander("View Excluded Files Details"):
                    for skip in inspection.skipped_items[:50]:
                        st.caption(skip)

    # ---------------- TAB 6: EXPORT ----------------
    with tab_export:
        st.subheader("Export Analysis Report")
        if not ai_report:
            st.warning("Generate AI analysis before exporting the full report.")
        else:
            md_content = export_report_to_markdown(inspection, ai_report)
            json_content = export_report_to_json(inspection, ai_report)

            c_exp1, c_exp2 = st.columns(2)
            with c_exp1:
                st.download_button(
                    label="📥 Download Markdown Report (.md)",
                    data=md_content,
                    file_name="reposage_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with c_exp2:
                st.download_button(
                    label="📥 Download JSON Report (.json)",
                    data=json_content,
                    file_name="reposage_report.json",
                    mime="application/json",
                    use_container_width=True,
                )

            st.markdown("#### Markdown Preview")
            st.text_area("Markdown Preview", value=md_content, height=350)
