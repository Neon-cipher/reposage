import { NextRequest, NextResponse } from "next/server";
import { validateGitHubUrl, URLValidationError } from "@/lib/repository/url-validator";
import { loadPublicRepository, RepositoryRetrievalError } from "@/lib/repository/repository-loader";
import { scanRepositoryFiles } from "@/lib/repository/file-scanner";
import { buildEvidenceIndex } from "@/lib/repository/evidence-index";
import { buildAnalysisPrompt, SYSTEM_INSTRUCTION } from "@/lib/ai/prompts";
import {
  checkOllamaHealth,
  generateOllamaCompletion,
  getOllamaModel,
  OllamaError,
} from "@/lib/ai/ollama-client";
import { parseAndCleanJson, buildValidatedAIReport } from "@/lib/report/report-generator";
import { exportReportToJson, exportReportToMarkdown } from "@/lib/report/export";

export async function POST(req: NextRequest) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON request body." }, { status: 400 });
  }

  const { url } = body || {};
  if (!url || typeof url !== "string") {
    return NextResponse.json(
      { error: "Missing required 'url' string parameter." },
      { status: 400 }
    );
  }

  // 1. Validate GitHub URL
  try {
    validateGitHubUrl(url);
  } catch (err: any) {
    if (err instanceof URLValidationError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    return NextResponse.json({ error: "URL validation failed." }, { status: 400 });
  }

  // 2. Verify local Ollama model availability
  const modelName = getOllamaModel();
  const health = await checkOllamaHealth(undefined, modelName);
  if (!health.connected) {
    return NextResponse.json(
      {
        error: `Local Ollama is offline or unreachable at ${health.configuredModel}. Please ensure 'ollama serve' is running.`,
      },
      { status: 503 }
    );
  }
  if (!health.modelVerified) {
    return NextResponse.json(
      {
        error: `Configured model '${modelName}' is not installed in local Ollama. Installed models: ${health.installedModels.join(", ")}.`,
      },
      { status: 500 }
    );
  }

  // 3. Retrieve public repository
  let loadedRepo;
  try {
    loadedRepo = await loadPublicRepository(url);
  } catch (err: any) {
    if (err instanceof RepositoryRetrievalError) {
      return NextResponse.json({ error: err.message }, { status: 422 });
    }
    return NextResponse.json(
      { error: "Failed to safely clone repository." },
      { status: 500 }
    );
  }

  try {
    // 4. Deterministic file scan
    const scanResult = await scanRepositoryFiles(loadedRepo.tempDir);
    // Replace tempDir in summary with canonical public repo identity
    scanResult.summary.rootPath = `https://github.com/${loadedRepo.identity.canonicalIdentity}`;

    // 5. Build evidence index
    const evidence = buildEvidenceIndex(scanResult.files);

    // 6. Construct prompt and query local Ollama
    const { prompt, evidenceMap } = buildAnalysisPrompt(scanResult.summary, evidence);
    const rawOutput = await generateOllamaCompletion(
      prompt,
      SYSTEM_INSTRUCTION,
      modelName,
      undefined,
      120000
    );

    // 7. Parse and validate AI JSON response
    const rawJson = parseAndCleanJson(rawOutput);
    const activeFilePaths = new Set(scanResult.files.keys());
    const aiReport = buildValidatedAIReport(rawJson, evidenceMap, activeFilePaths);

    // 8. Generate exports
    const markdownExport = exportReportToMarkdown(scanResult.summary, aiReport, modelName);
    const jsonExport = exportReportToJson(
      scanResult.summary,
      aiReport,
      modelName,
      evidence.candidateEntrypoints,
      evidence.runCommands,
      evidence.testCommands
    );

    // 9. Return structured analysis result
    return NextResponse.json({
      status: "success",
      metadata: {
        canonicalIdentity: loadedRepo.identity.canonicalIdentity,
        normalizedUrl: loadedRepo.identity.normalizedUrl,
        modelName,
        filesScanned: scanResult.summary.totalFilesScanned,
        linesOfCode: scanResult.summary.totalLines,
        excludedFilesCount: scanResult.excludedFilesCount,
      },
      summary: scanResult.summary,
      evidenceIndex: evidence.records,
      aiReport,
      exports: {
        markdown: markdownExport,
        json: jsonExport,
      },
    });
  } catch (err: any) {
    if (err instanceof OllamaError) {
      return NextResponse.json({ error: err.message }, { status: 502 });
    }
    return NextResponse.json(
      { error: `Analysis processing failed: ${err.message}` },
      { status: 500 }
    );
  } finally {
    // 10. Clean up temporary directory
    await loadedRepo.cleanup();
  }
}
