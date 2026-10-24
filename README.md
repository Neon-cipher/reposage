# 🌿 RepoSage

> **Small Open-Source AI Repository Analyst for Hacktoberfest**
> 
> *Helping developers orient themselves in unfamiliar repositories and find beginner-friendly contribution opportunities without executing untrusted code.*

---

## 🚀 Key Features

- 🌐 **Public Repository URL Analysis**: Securely analyzes public GitHub repositories via shallow clone into an isolated sandbox, automatically cleaning up temporary files after analysis.
- 🛡️ **SSRF & Rebinding Protection**: Strict HTTPS allowlist, rejection of private/internal IPs, localhost, custom ports, and embedded credentials.
- 🔍 **Strict Deterministic Inspection**: Traverses repositories safely without executing repository code or installing untrusted dependencies.
- 🛡️ **Zero-Trust Exclusions**: Automatically excludes `.git`, `.venv`, `node_modules`, binary artifacts, and credential files (`.env`, `.pem`, `.key`).
- 🤖 **Local Ollama Integration**: Powered entirely by local models (`qwen2.5`, `llama3.2`) via Ollama's HTTP API. Zero data leaves your machine.
- ⚖️ **Tripartite Finding Classification**:
  - **Facts**: Proven directly from AST, configs, file trees, and tests.
  - **Inferences**: Deductions by the AI about architecture and logic flow.
  - **Unknowns**: Transparently marked gaps requiring developer verification.
- 🎯 **Hacktoberfest Opportunity Engine**:
  - Discovers high-impact `Good First Issues`.
  - Flags unaddressed `TODO` / `FIXME` comments with exact line citations.
  - Identifies documentation gaps and missing test coverage.
- 🖥️ **Streamlit UI**: Clean, interactive dashboard supporting both Local Folders and Public Git URLs.

---

## 🛠️ Architecture

```
d:\reposage\
├── src\reposage\
│   ├── scanner.py          # Deterministic safe file traversal & metrics
│   ├── analyzers\
│   │   ├── python_ast.py   # Python AST entrypoint & symbol parsing
│   │   └── generic.py      # Regex & heuristic JS/TS, config, and TODO extractor
│   ├── models.py           # Core dataclasses and citation models
│   ├── ollama_client.py    # Robust HTTP client for local Ollama API
│   ├── prompts.py          # Grounded prompts with anti-injection fences
│   └── reporter.py         # Synthesis of facts, inferences, and opportunities
├── tests\                  # Comprehensive unit tests
├── app.py                  # Streamlit dashboard
├── requirements.txt        # Dependencies
├── pyproject.toml          # Build configuration
└── LICENSE                 # MIT License
```

---

## 📦 Getting Started

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) installed and running locally:
  ```bash
  ollama serve
  ollama run qwen2.5:latest
  # or
  ollama run llama3.2:1b
  ```

#### Supported Local Models Provenance & Licensing:
- **Qwen 2.5 (`qwen2.5:latest` / 7B)**: Developed by the Qwen Team (Alibaba Cloud), licensed under the Apache 2.0 License. Recommended for comprehensive architecture deductions and detailed roadmaps.
- **Llama 3.2 (`llama3.2:1b` / 1.2B)**: Developed by Meta, licensed under the Meta Llama 3.2 Community License. Recommended for low-latency, resource-constrained laptop environments.

#### Environment Variables (Optional):
- `OLLAMA_URL`: URL of the local Ollama daemon (defaults to `http://localhost:11434`).
- `OLLAMA_MODEL`: Model tag to invoke (defaults to `qwen2.5:latest`).


### 2. Installation
```bash
git clone https://github.com/your-org/reposage.git
cd reposage
pip install -e .
```

### 3. Launching the Dashboard
```bash
streamlit run app.py
```

### 5. Quick Demo with Sample Repository
RepoSage comes with a harmless sample repository inside `sample_repo/` for instant evaluation:
1. Start the app: `streamlit run app.py`
2. Enter the path `sample_repo/` (or absolute path) in the sidebar.
3. Click **"1. Static Scan"** to preview the deterministic inventory and evidence index.
4. Click **"2. Run AI"** to generate the evidence-grounded overview, architecture breakdown, and contribution roadmap.
5. Explore the **"Cited Evidence"** tab to verify that every finding cites exact file lines.
6. Export the report via the **"Export Report"** tab as Markdown or JSON.

---

## ⚠️ Known Limitations

1. **Static Inspection Only**: RepoSage statically parses source text and AST. It does not run test suites or execute repository build scripts by design.
2. **Context Window Capping**: Salient repository evidence is ranked and capped at the top 50 items to fit standard 4k-8k local LLM context limits reliably.
3. **JS/TS Parsing**: JavaScript and TypeScript symbol and import analysis is heuristic and pattern-based rather than utilizing a full TypeScript compiler service.

---

## 🙏 Acknowledgements & Attribution

- **AI Pair Programming**: Developed in pair programming collaboration with **Google DeepMind's Antigravity agentic assistant (powered by Gemini 3.8 Flash)**.
- **Local Inference Engine**: Powered by **[Ollama](https://ollama.ai)**.
- **Underlying Models**:
  - `qwen2.5:latest` (Alibaba Cloud, Apache 2.0 License).
  - `llama3.2:1b` (Meta, Llama 3.2 Community License).
- **Web Interface**: Built with **[Streamlit](https://streamlit.io)** (Apache 2.0).

---

## 📄 License

Distributed under the [MIT License](LICENSE).

