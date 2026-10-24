import os
import streamlit as st
from pathlib import Path
from reposage.scanner import scan_repository
from reposage.ollama_client import OllamaClient
from reposage.reporter import analyze_repository_pipeline
from reposage.models import FindingCategory

st.set_page_config(
    page_title="RepoSage - AI Repository Analyst",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Hacktoberfest & High-End Aesthetic
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1e2430;
        border: 1px solid #2e384d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-fact {
        background-color: #10402b;
        color: #4ade80;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-inference {
        background-color: #3b2816;
        color: #facc15;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-unknown {
        background-color: #372023;
        color: #f87171;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .opportunity-card {
        background: linear-gradient(135deg, #182234 0%, #1a1e29 100%);
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar Configuration
with st.sidebar:
    st.title("🌿 RepoSage")
    st.caption("AI-Assisted Repo Orientation & Hacktoberfest Finder")

    st.subheader("1. Ollama Inference Setup")
    ollama_url = st.text_input("Ollama Endpoint", value="http://localhost:11434")
    
    client = OllamaClient(base_url=ollama_url)
    health = client.check_health()
    
    if health["status"] == "ok":
        st.success("Ollama Connected")
        available_models = health["models"]
        if not available_models:
            available_models = ["qwen2.5:latest", "llama3.2:1b"]
    else:
        st.error(f"Ollama Unreachable: {health.get('error')}")
        available_models = ["qwen2.5:latest"]

    selected_model = st.selectbox("Inference Model", options=available_models, index=0)

    st.markdown("---")
    st.subheader("2. Target Repository")
    default_path = str(Path(os.getcwd()).resolve())
    target_dir = st.text_input("Local Folder Path", value=default_path)

    analyze_btn = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown(
        """
        **Hacktoberfest Guarantees:**
        - 🔒 No code execution or dependencies run
        - 🛡️ Strict exclusions (.git, secrets, binaries)
        - 📌 Deterministic facts vs AI deductions
        - 🏷️ Exact code line citations
        """
    )

# Main Dashboard
st.header("Repository Intelligence & Onboarding Dashboard")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if analyze_btn:
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        st.error(f"Specified path does not exist or is not a folder: `{target_dir}`")
    else:
        with st.spinner(f"Deterministically scanning & reasoning with `{selected_model}`..."):
            try:
                res = analyze_repository_pipeline(
                    repo_path=target_dir,
                    ollama_client=client,
                    model_name=selected_model,
                )
                st.session_state.analysis_result = res
                st.success(f"Analysis completed in {res.analysis_duration_sec:.2f}s using {res.model_name}")
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")

result = st.session_state.analysis_result

if result:
    facts = result.facts

    # Top KPI Metrics Row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Scanned Files", facts.total_files_scanned)
    with c2:
        st.metric("Lines of Code", f"{facts.total_lines:,}")
    with c3:
        top_lang = max(facts.language_counts.items(), key=lambda x: x[1])[0] if facts.language_counts else "None"
        st.metric("Primary Language", top_lang)
    with c4:
        st.metric("Discovered TODOs", len(facts.todos))
    with c5:
        st.metric("Test Suite Present", "✅ Yes" if facts.has_tests else "❌ No")

    st.markdown("---")

    # Tabs
    tab_opps, tab_arch, tab_findings, tab_facts = st.tabs(
        [
            "🎯 Hacktoberfest Opportunities",
            "🏛️ Architecture & Orientation",
            "⚖️ Facts vs Inferences vs Unknowns",
            "📊 Deterministic Fact Sheet",
        ]
    )

    # 1. Opportunities Tab
    with tab_opps:
        st.subheader("Beginner-Friendly Contribution Opportunities")
        st.caption("Actionable issues, missing tests, and refactors linked to exact files and lines.")

        if not result.opportunities:
            st.info("No specific high-priority opportunities detected. Check TODOs and test coverage below.")
        else:
            for opp in result.opportunities:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="opportunity-card">
                            <h4 style="margin:0 0 8px 0; color:#38bdf8;">{opp.title}</h4>
                            <p><strong>Difficulty:</strong> <span style="color:#4ade80;">{opp.difficulty}</span> | <strong>Target File:</strong> <code>{opp.file_path}</code> {f' (Line {opp.line_number})' if opp.line_number else ''}</p>
                            <p>{opp.rationale}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if opp.action_items:
                        st.markdown("**Actionable Steps:**")
                        for step in opp.action_items:
                            st.markdown(f"- {step}")
                    if opp.pr_template_suggestion:
                        st.caption(f"Suggested PR Title: `{opp.pr_template_suggestion}`")
                    st.divider()

    # 2. Architecture Tab
    with tab_arch:
        st.subheader("Repository Overview & Architectural Orientation")
        st.markdown("#### Summary Overview")
        st.info(result.summary_overview)

        st.markdown("#### Structural Architecture")
        st.write(result.architecture_overview)

        st.markdown("#### Entrypoints Identified")
        if facts.entrypoints:
            for ep in facts.entrypoints:
                st.markdown(f"- **`{ep.format_citation()}`**")
                if ep.snippet:
                    st.code(ep.snippet, language="python")
        else:
            st.caption("No explicit `__main__` or server `.listen` entrypoints detected.")

    # 3. Facts vs Inferences vs Unknowns Matrix
    with tab_findings:
        st.subheader("Evidence-Backed Findings Matrix")
        st.caption("Explicitly separating verified facts from AI-generated deductions and unverified unknowns.")

        filter_category = st.radio(
            "Filter Findings Category",
            ["All", "Facts", "Inferences", "Unknowns"],
            horizontal=True,
        )

        for finding in result.findings:
            if filter_category == "Facts" and finding.category != FindingCategory.FACT:
                continue
            if filter_category == "Inferences" and finding.category != FindingCategory.INFERENCE:
                continue
            if filter_category == "Unknowns" and finding.category != FindingCategory.UNKNOWN:
                continue

            badge_class = (
                "badge-fact"
                if finding.category == FindingCategory.FACT
                else ("badge-inference" if finding.category == FindingCategory.INFERENCE else "badge-unknown")
            )
            cat_name = finding.category.value.upper()

            with st.container():
                citation_html = (
                    f" | <code>{finding.citation.format_citation()}</code>"
                    if finding.citation
                    else ""
                )
                st.markdown(
                    f"""
                    <div style="margin-bottom: 10px;">
                        <span class="{badge_class}">[{cat_name}]</span> <strong>{finding.title}</strong> {citation_html}
                        <p style="margin-top: 6px; color: #cbd5e1;">{finding.description}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.divider()

    # 4. Deterministic Fact Sheet
    with tab_facts:
        st.subheader("Deterministic Repository Inspection")
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("#### Languages by File Count")
            st.json(facts.language_counts)

            st.markdown("#### Governance & Documentation")
            st.markdown(f"- **README**: {'✅ Present (' + facts.readme_path + ')' if facts.has_readme else '❌ Missing'}")
            st.markdown(f"- **CONTRIBUTING**: {'✅ Present (' + facts.contributing_path + ')' if facts.has_contributing else '❌ Missing'}")
            st.markdown(f"- **LICENSE**: {'✅ Present (' + str(facts.license_type) + ')' if facts.has_license else '❌ Missing'}")

        with col_r:
            st.markdown("#### Declared Dependencies")
            if facts.dependencies:
                st.code("\n".join(facts.dependencies[:20]), language="text")
            else:
                st.caption("No declared dependencies detected.")

            st.markdown("#### Discovered Code Tags (TODO / FIXME)")
            if facts.todos:
                for td in facts.todos[:10]:
                    st.markdown(f"- **[{td.tag}]** `{td.file_path}:L{td.line_number}`: *{td.text}*")
            else:
                st.caption("No TODO or FIXME comments found.")

        if facts.skipped_items:
            with st.expander(f"View Skipped / Excluded Items ({len(facts.skipped_items)})"):
                for it in facts.skipped_items:
                    st.caption(f"- {it}")
else:
    st.info("👈 Enter a local repository folder path in the sidebar and click **Analyze Repository** to get started.")
