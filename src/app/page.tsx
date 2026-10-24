"use client";

import React, { useState, useEffect } from "react";
import {
  Search,
  Terminal,
  ShieldCheck,
  Cpu,
  Layers,
  FileCode,
  Download,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  GitBranch,
  BookOpen,
} from "lucide-react";

export default function Home() {
  const [url, setUrl] = useState("https://github.com/psf/requests");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "architecture" | "roadmap" | "evidence" | "export">("overview");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => setHealth(data.ai))
      .catch(() => setHealth({ connected: false, error: "Health check failed" }));
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    setLoadingStep("Validating GitHub URL & checking accessibility...");

    try {
      setLoadingStep("Performing shallow clone into isolated sandbox...");
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Analysis failed");
      }

      setResult(data);
      setActiveTab("overview");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  };

  const downloadFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const u = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = u;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(u);
  };

  return (
    <main className="max-w-7xl mx-auto px-4 py-8 font-sans">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-border gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌿</span>
            <h1 className="text-2xl font-bold tracking-tight text-white">RepoSage</h1>
            <span className="text-xs px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800 font-mono">
              Next.js & local AI
            </span>
          </div>
          <p className="text-sm text-muted mt-1">
            Deterministic static inspection & evidence-grounded local AI repository analyst.
          </p>
        </div>

        {/* Model status pill */}
        <div className="flex items-center gap-3 bg-surface border border-border px-3 py-1.5 rounded-lg text-xs">
          <div className="flex items-center gap-1.5">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                health?.connected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-slate-300 font-medium">Local Ollama</span>
          </div>
          <span className="text-muted">|</span>
          <span className="font-mono text-sky-400">
            {health?.configuredModel || "qwen2.5:latest"}
          </span>
          {health?.modelVerified && (
            <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800">
              verified
            </span>
          )}
        </div>
      </header>

      {/* Input section */}
      <section className="mt-8 bg-surface/50 border border-border rounded-xl p-6">
        <form onSubmit={handleAnalyze} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-muted" />
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-border rounded-lg text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              "Analyze Repository"
            )}
          </button>
        </form>

        {loading && (
          <div className="mt-4 flex items-center gap-2 text-xs text-sky-400 font-mono">
            <span className="animate-pulse">▶</span>
            <span>{loadingStep || "Processing..."}</span>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-800/80 rounded-lg flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Analysis Error</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}
      </section>

      {/* Results dashboard */}
      {result && (
        <section className="mt-8 space-y-6">
          {/* Top metadata row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-surface border border-border rounded-lg p-4">
              <span className="text-xs text-muted">Repository</span>
              <p className="text-sm font-semibold text-white mt-1 truncate">
                {result.metadata.canonicalIdentity}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-lg p-4">
              <span className="text-xs text-muted">Scanned Files</span>
              <p className="text-sm font-semibold text-white mt-1">
                {result.metadata.filesScanned}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-lg p-4">
              <span className="text-xs text-muted">Lines of Code</span>
              <p className="text-sm font-semibold text-white mt-1">
                {result.metadata.linesOfCode.toLocaleString()}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-lg p-4">
              <span className="text-xs text-muted">Evidence Citations</span>
              <p className="text-sm font-semibold text-emerald-400 mt-1">
                {result.aiReport.stats.totalEvidenceCited} validated
              </p>
            </div>
          </div>

          {/* Navigation tabs */}
          <div className="flex border-b border-border gap-2">
            {[
              { id: "overview", label: "Overview", icon: BookOpen },
              { id: "architecture", label: "Architecture", icon: Layers },
              { id: "roadmap", label: "Contribution Roadmap", icon: GitBranch },
              { id: "evidence", label: "Cited Evidence", icon: FileCode },
              { id: "export", label: "Export Report", icon: Download },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-sky-400 text-sky-400"
                      : "border-transparent text-muted hover:text-slate-300"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab contents */}
          <div className="space-y-6">
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                <div className="bg-surface border border-border rounded-lg p-5">
                  <h3 className="text-sm font-semibold text-white">Project Purpose</h3>
                  <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                    {result.aiReport.overview.purpose}
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-surface border border-border rounded-lg p-5">
                    <h3 className="text-sm font-semibold text-white">Main Components</h3>
                    <ul className="mt-3 space-y-2 text-xs text-slate-300">
                      {result.aiReport.overview.mainComponents.map((c: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-sky-400 font-mono">•</span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-surface border border-border rounded-lg p-5">
                    <h3 className="text-sm font-semibold text-white">Technologies</h3>
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {result.aiReport.overview.keyTechnologies.map((t: string, i: number) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 bg-slate-800 text-slate-200 text-xs rounded border border-slate-700 font-mono"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Grounded findings */}
                <div className="bg-surface border border-border rounded-lg p-5">
                  <h3 className="text-sm font-semibold text-white mb-3">Grounded Findings</h3>
                  <div className="space-y-3">
                    {result.aiReport.overview.findings.map((f: any, i: number) => (
                      <div key={i} className="text-xs border-l-2 border-slate-700 pl-3 py-0.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
                              f.nature === "observation"
                                ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                                : "bg-amber-950 text-amber-400 border border-amber-800"
                            }`}
                          >
                            {f.nature.toUpperCase()}
                          </span>
                          <span className="text-slate-200">{f.statement}</span>
                        </div>
                        {f.citations?.length > 0 && (
                          <div className="mt-1 text-[11px] text-muted font-mono">
                            Citations:{" "}
                            {f.citations.map((c: any, ci: number) => (
                              <span key={ci} className="text-sky-400 mr-2">
                                {c.evidenceId} ({c.filePath}:{c.lineRange})
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ARCHITECTURE TAB */}
            {activeTab === "architecture" && (
              <div className="space-y-6">
                <div className="bg-surface border border-border rounded-lg p-5">
                  <h3 className="text-sm font-semibold text-white">System Architecture</h3>
                  <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                    {result.aiReport.architecture.systemOverview}
                  </p>
                </div>

                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-white">Evidenced Modules</h3>
                  {result.aiReport.architecture.modules.map((m: any, i: number) => (
                    <div key={i} className="bg-surface border border-border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm text-sky-400 font-semibold">{m.name}</span>
                        <span className="text-xs text-muted font-mono">{m.filePath}</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-300">{m.responsibilities}</p>

                      <div className="grid md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-border/60 text-xs">
                        <div>
                          <span className="text-muted block mb-1">Verified Imports:</span>
                          {m.verifiedImports?.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {m.verifiedImports.map((imp: string, ii: number) => (
                                <span key={ii} className="font-mono bg-slate-800/80 px-1.5 py-0.5 rounded text-[11px]">
                                  {imp}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-muted italic">None verified</span>
                          )}
                        </div>

                        <div>
                          <span className="text-muted block mb-1">Inferred Runtime Relationships:</span>
                          {m.inferredRuntimeRelationships?.length > 0 ? (
                            <ul className="space-y-1">
                              {m.inferredRuntimeRelationships.map((rel: string, ri: number) => (
                                <li key={ri} className="text-slate-300 italic text-[11px]">
                                  • {rel}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-muted italic">None inferred</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ROADMAP TAB */}
            {activeTab === "roadmap" && (
              <div className="space-y-6">
                {result.aiReport.roadmap.generalGuidance && (
                  <div className="bg-surface border border-border rounded-lg p-4 text-xs text-slate-300">
                    <span className="font-semibold text-white block mb-1">Maintainer Guidance:</span>
                    {result.aiReport.roadmap.generalGuidance}
                  </div>
                )}

                <div className="space-y-4">
                  {result.aiReport.roadmap.tasks.map((task: any, i: number) => (
                    <div
                      key={i}
                      className={`bg-surface border rounded-lg p-5 ${
                        task.isSpeculative ? "border-purple-900/60" : "border-sky-900/60"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold text-white">
                          Task {i + 1}: {task.title}
                        </h4>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                            task.isSpeculative
                              ? "bg-purple-950 text-purple-400 border-purple-800"
                              : "bg-sky-950 text-sky-400 border-sky-800"
                          }`}
                        >
                          {task.isSpeculative ? "SPECULATIVE" : "EVIDENCED"}
                        </span>
                      </div>

                      <p className="mt-2 text-xs text-slate-300">{task.rationale}</p>

                      <div className="grid md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-border text-xs">
                        <div>
                          <span className="text-muted block font-medium mb-1">Relevant Files:</span>
                          <div className="space-y-1 font-mono text-[11px] text-sky-400">
                            {task.relevantFiles.map((f: string, fi: number) => (
                              <div key={fi}>• {f}</div>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="text-muted block font-medium mb-1">Validation Steps:</span>
                          <ul className="space-y-1 text-slate-300 text-[11px]">
                            {task.validationSuggestions.map((v: string, vi: number) => (
                              <li key={vi}>✓ {v}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* EVIDENCE TAB */}
            {activeTab === "evidence" && (
              <div className="space-y-4">
                <div className="text-xs text-muted">
                  Showing {result.evidenceIndex.length} grounded repository evidence excerpts.
                </div>
                <div className="space-y-3">
                  {result.evidenceIndex.slice(0, 50).map((ev: any, i: number) => (
                    <div key={i} className="bg-surface border border-border rounded-lg p-3 text-xs">
                      <div className="flex items-center justify-between font-mono text-[11px] mb-2">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-sky-400 border border-slate-700">
                            {ev.id}
                          </span>
                          <span className="text-slate-200">{ev.filePath}</span>
                        </div>
                        <span className="text-muted">
                          L{ev.startLine}-L{ev.endLine}
                        </span>
                      </div>
                      <pre className="p-2.5 bg-background border border-border/80 rounded font-mono text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                        {ev.snippet}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* EXPORT TAB */}
            {activeTab === "export" && (
              <div className="space-y-4 bg-surface border border-border rounded-lg p-6">
                <h3 className="text-sm font-semibold text-white">Export Analysis Report</h3>
                <p className="text-xs text-muted">
                  Download the validated report including timestamp, provenance, and provisional disclaimers.
                </p>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() =>
                      downloadFile(
                        result.exports.markdown,
                        `reposage_${result.metadata.canonicalIdentity.replace("/", "_")}.md`,
                        "text/markdown"
                      )
                    }
                    className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-medium transition-colors flex items-center gap-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Markdown (.md)
                  </button>
                  <button
                    onClick={() =>
                      downloadFile(
                        result.exports.json,
                        `reposage_${result.metadata.canonicalIdentity.replace("/", "_")}.json`,
                        "application/json"
                      )
                    }
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium border border-border transition-colors flex items-center gap-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download JSON (.json)
                  </button>
                </div>

                <div className="mt-4">
                  <span className="text-xs text-muted block mb-2 font-mono">Markdown Preview:</span>
                  <textarea
                    readOnly
                    value={result.exports.markdown}
                    rows={12}
                    className="w-full p-3 bg-background border border-border rounded font-mono text-xs text-slate-300 focus:outline-none"
                  />
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
