import { NextResponse } from "next/server";
import { checkOllamaHealth } from "@/lib/ai/ollama-client";

export async function GET() {
  try {
    const health = await checkOllamaHealth();
    return NextResponse.json({
      status: "ok",
      version: "0.2.0",
      ai: {
        connected: health.connected,
        configuredModel: health.configuredModel,
        modelVerified: health.modelVerified,
        installedModelsCount: health.installedModels.length,
        error: health.error,
      },
    });
  } catch (err: any) {
    return NextResponse.json(
      {
        status: "error",
        error: "Failed to evaluate system health.",
      },
      { status: 500 }
    );
  }
}
