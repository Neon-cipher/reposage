# 🌿 RepoSage

> **Production-Minded Next.js & Local Open-Weight AI Repository Analyst**
> 
> *Helping developers orient themselves in unfamiliar public repositories and find beginner-friendly contribution opportunities without executing untrusted code or sending data to the cloud.*

---

## 🚀 Key Features

- 🌐 **Public GitHub Repository Analysis**: Securely analyzes public GitHub repositories via shallow clone into an isolated sandbox, automatically destroying temporary files after analysis.
- 🛡️ **SSRF & DNS Rebinding Defenses**: Strict HTTPS allowlist (`github.com`), rejection of private/internal IPs, localhost, custom ports, and embedded credentials.
- 🔍 **Deterministic File Inspection**: Traverses repositories safely without executing repository code, build scripts, or installing dependencies.
- 🛡️ **Zero-Trust Exclusions**: Automatically excludes `.git`, `.venv`, `node_modules`, binary artifacts, and credential files (`.env`, `.pem`, `.key`).
- 🤖 **Local Ollama Integration**: Powered entirely by local models (`qwen2.5`, `llama3.2`) via Ollama's HTTP API. Zero data leaves your machine.
- ⚖️ **Tripartite Finding Classification**:
  - **Observations**: Directly proven from code AST, manifests, file trees, and tests.
  - **Inferences**: Deductions by the AI about architecture and runtime logic flow.
  - **Unknowns**: Transparently marked gaps requiring developer verification.
- 🎯 **Beginner Contribution Opportunities**:
  - Highlights beginner tasks with exact file links, prerequisites, and test validation commands.
  - Distinguishes evidenced tasks from speculative recommendations.
- 🖥️ **Professional Minimal UI**: Next.js App Router, Tailwind CSS dark theme, near-black aesthetics, and instant JSON/Markdown report exports.

---

## 🛠️ Architecture

```
d:\reposage\
├── src\
│   ├── app\
│   │   ├── api\
│   │   │   ├── analyze\route.ts    # POST /api/analyze (orchestration & inference)
│   │   │   └── health\route.ts     # GET /api/health (Ollama & system status)
│   │   ├── globals.css             # Tailwind base styles
│   │   ├── layout.tsx              # Root HTML layout
│   │   └── page.tsx                # Professional developer landing & dashboard
│   └── lib\
│       ├── ai\
│       │   ├── ollama-client.ts    # Local Ollama HTTP API client
│       │   ├── prompts.ts          # Grounded prompt builder with anti-injection fences
│       │   └── response-validator.ts # Zod schema for structured output
│       ├── report\
│       │   ├── export.ts           # JSON & GitHub-flavored Markdown exporter
│       │   └── report-generator.ts # Citation resolver & hallucination checker
│       └── repository\
│           ├── evidence-index.ts   # Stable evidence ID indexing
│           ├── file-scanner.ts     # Static text traversal, size limits, secret detector
│           ├── repository-loader.ts # Shallow clone sandbox with automated cleanup
│           └── url-validator.ts    # Strict URL validation & SSRF defense
├── tests\
│   ├── report-generator.test.ts    # Vitest report validation & export tests
│   ├── scanner.test.ts             # Vitest scanner and evidence tests
│   └── url-validator.test.ts       # Vitest URL and SSRF tests
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── vitest.config.ts
```

---

## 📦 Getting Started

### 1. Prerequisites
- Node.js 18+ (verified on v24.18.0)
- Git CLI
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
git clone https://github.com/Neon-cipher/reposage.git
cd reposage
npm install
```

### 3. Launching the Development Server
```bash
npm run dev
# or for production:
npm run build
npm start
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

### 4. Running Unit Tests
```bash
npm test
```

---

## ⚡ Live Demo Walkthrough

1. Open **[http://localhost:3000](http://localhost:3000)**.
2. Check the **Local Ollama** status pill in the top header (indicates model presence and verification).
3. Paste a public GitHub repository URL into the input field:
   `https://github.com/psf/requests` or `https://github.com/octocat/Hello-World`
4. Click **"Analyze Repository"**.
5. Observe the multi-stage progress (validating URL → shallow clone → static scan → local AI inference).
6. Explore the generated tabs:
   - **Overview**: Purpose, audience, components, technologies, and grounded findings.
   - **Architecture**: System architecture with verified imports vs. inferred runtime relationships.
   - **Contribution Roadmap**: High-value beginner tasks with exact target files and validation steps.
   - **Cited Evidence**: All verbatim code excerpts cited in the findings.
   - **Export Report**: Downloadable Markdown and JSON formats with UTC timestamp and provisional notice.

---

## ⚠️ Known Limitations

1. **Static Inspection Only**: RepoSage statically parses source text and AST. It does not run test suites or execute repository build scripts by design.
2. **Context Window Capping**: Salient repository evidence is ranked and capped at the top 40-50 items to fit standard 4k-8k local LLM context limits reliably.
3. **Provider Scope**: Prioritizes public GitHub repositories. Direct IP hosts and private repositories are intentionally disallowed.

---

## 🙏 Acknowledgements & Attribution

- **AI Pair Programming**: Developed in pair programming collaboration with **Google DeepMind's Antigravity agentic assistant (powered by Gemini 3.8 Flash)**.
- **Local Inference Engine**: Powered by **[Ollama](https://ollama.ai)**.
- **Underlying Models**:
  - `qwen2.5:latest` (Alibaba Cloud, Apache 2.0 License).
  - `llama3.2:1b` (Meta, Llama 3.2 Community License).
- **Web Stack**: Built with **Next.js 15**, **React 19**, **Tailwind CSS**, and **Vitest**.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
