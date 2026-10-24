import { describe, it, expect } from "vitest";
import path from "path";
import { scanRepositoryFiles, isPathContained, containsSecretPattern } from "@/lib/repository/file-scanner";
import { buildEvidenceIndex } from "@/lib/repository/evidence-index";

describe("Deterministic File Scanner & Evidence Index", () => {
  const sampleRepoPath = path.resolve(__dirname, "../sample_repo");

  it("scans eligible repository files without executing code", async () => {
    const res = await scanRepositoryFiles(sampleRepoPath);
    expect(res.summary.totalFilesScanned).toBeGreaterThanOrEqual(4);
    expect(res.summary.hasReadme).toBe(true);
    expect(res.summary.importantManifests).toContain("pyproject.toml");
    expect(res.files.has("src/sample.py")).toBe(true);
    expect(res.files.has("tests/test_sample.py")).toBe(true);
  });

  it("indexes candidate entrypoints and evidence citations accurately", async () => {
    const scan = await scanRepositoryFiles(sampleRepoPath);
    const index = buildEvidenceIndex(scan.files);

    expect(index.records.length).toBeGreaterThan(0);
    // Verified entrypoint guard in sample.py
    expect(index.candidateEntrypoints.some((e) => e.includes("src/sample.py"))).toBe(true);
    // Verified run command in README
    expect(index.runCommands.some((c) => c.includes("sample.py"))).toBe(true);
  });

  it("checks path containment correctly", () => {
    expect(isPathContained("/root/repo", "/root/repo/src/file.ts")).toBe(true);
    expect(isPathContained("/root/repo", "/root/outside/secret.txt")).toBe(false);
  });

  it("detects secret patterns without exposing values", () => {
    expect(containsSecretPattern("const key = 'AKIA1234567890ABCDEF';")).toBe(true);
    expect(containsSecretPattern("-----BEGIN RSA PRIVATE KEY-----")).toBe(true);
    expect(containsSecretPattern("const normal = 'hello world';")).toBe(false);
  });
});
