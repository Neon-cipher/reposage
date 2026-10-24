import { describe, it, expect } from "vitest";
import { parseAndCleanJson, buildValidatedAIReport } from "@/lib/report/report-generator";
import { EvidenceRecord } from "@/lib/repository/evidence-index";
import { exportReportToMarkdown, exportReportToJson } from "@/lib/report/export";

describe("AI Report Generator & Validation", () => {
  it("cleans markdown fences and parses valid JSON", () => {
    const raw = "```json\n{\"project_overview\": {\"purpose\": \"Demo project\"}}\n```";
    const res = parseAndCleanJson(raw);
    expect(res.project_overview.purpose).toBe("Demo project");
  });

  it("handles model 'or' artifacts cleanly", () => {
    const raw = "{\"nature\": \"observation\" or \"inference\"}";
    const res = parseAndCleanJson(raw);
    expect(res.nature).toBe("observation");
  });

  it("flags nonexistent evidence IDs", () => {
    const evidenceMap = new Map<string, EvidenceRecord>();
    evidenceMap.set("ev_1", {
      id: "ev_1",
      filePath: "src/main.ts",
      category: "entrypoint",
      description: "Main entry",
      startLine: 1,
      endLine: 5,
      snippet: "console.log('hi');",
    });

    const mockAi = {
      project_overview: {
        purpose: "Test repo",
        main_components: [],
        likely_audience: "Devs",
        key_technologies: [],
        findings: [
          { nature: "observation", statement: "Valid finding", evidence_ids: ["ev_1"] },
          { nature: "observation", statement: "Hallucinated finding", evidence_ids: ["ev_999"] },
        ],
        unknowns: [],
      },
      architecture_explanation: { system_overview: "Simple", modules: [], findings: [], unknowns: [] },
      contribution_roadmap: {
        general_guidance: "",
        tasks: [
          {
            title: "Task 1",
            is_speculative: false,
            rationale: "Fix bug",
            relevant_files: ["src/main.ts"],
            prerequisites: [],
            validation_suggestions: [],
            evidence_ids: ["ev_1"],
          },
        ],
        findings: [],
        unknowns: [],
      },
    };

    const report = buildValidatedAIReport(mockAi, evidenceMap, new Set(["src/main.ts"]));
    expect(report.stats.rejectedEvidenceIds).toContain("ev_999");
    expect(report.overview.findings[0].isFlagged).toBe(false);
    expect(report.overview.findings[1].isFlagged).toBe(true);
  });

  it("exports report to markdown with timestamp and disclaimers", () => {
    const dummySummary: any = {
      rootPath: "https://github.com/test/repo",
      totalFilesScanned: 5,
      totalLines: 150,
      documentationScore: 0.8,
      languages: { TypeScript: 5 },
      importantManifests: ["package.json"],
      testDirectories: [],
      skippedReasons: {},
    };

    const dummyReport: any = {
      overview: {
        purpose: "A test project",
        mainComponents: ["Core"],
        likelyAudience: "Developers",
        keyTechnologies: ["TypeScript"],
        findings: [],
        unknowns: [],
      },
      architecture: { systemOverview: "Modular", modules: [], findings: [], unknowns: [] },
      roadmap: { generalGuidance: "", tasks: [], findings: [], unknowns: [] },
      stats: { totalEvidenceProvided: 5, totalEvidenceCited: 2, rejectedEvidenceIds: [] },
    };

    const md = exportReportToMarkdown(dummySummary, dummyReport, "qwen2.5:latest");
    expect(md).toContain("# RepoSage Analysis Report");
    expect(md).toContain("PROVISIONAL NOTICE");
    expect(md).toContain("qwen2.5:latest");

    const jsonStr = exportReportToJson(dummySummary, dummyReport, "qwen2.5:latest");
    const parsed = JSON.parse(jsonStr);
    expect(parsed.metadata.model).toBe("qwen2.5:latest");
    expect(parsed.metadata.disclaimer).toContain("PROVISIONAL NOTICE");
  });
});
