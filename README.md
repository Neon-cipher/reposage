# 🌿 RepoSage

> **Small Open-Source AI Repository Analyst for Hacktoberfest**
> 
> *Helping developers orient themselves in unfamiliar repositories and find beginner-friendly contribution opportunities without executing untrusted code.*

---

## 🚀 Key Features

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
- 🖥️ **Streamlit UI**: Clean, interactive dashboard for repository exploration.

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

### 4. Running Tests
```bash
pytest
```

---

## 🛡️ Safety & Responsible AI

- **No Remote Calls**: All analysis is computed locally via the local Ollama daemon at `http://localhost:11434`.
- **Anti-Prompt Injection**: Repository snippets are treated as untrusted text, wrapped in delimited blocks, and forbidden from overriding instructions.
- **Evidence-Based Citations**: Findings and opportunities link to verifiable file paths and line ranges.

---

## 📄 License

Distributed under the [MIT License](file:///d:/reposage/LICENSE).
