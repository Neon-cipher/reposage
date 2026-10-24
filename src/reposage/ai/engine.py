from typing import Optional
from reposage.inspector_models import InspectionResult
from reposage.ai.ollama_client import LocalOllamaClient
from reposage.ai.ai_models import AIAnalysisReport
from reposage.ai.prompt_engine import (
    SYSTEM_INSTRUCTION,
    prepare_bounded_evidence_index,
    build_analysis_payload,
)
from reposage.ai.validator import parse_and_clean_json, build_validated_report


class AIAnalysisEngine:
    """
    Orchestrates the local AI analysis layer:
    1. Prepares bounded repository evidence with sequential stable IDs.
    2. Constructs grounded, anti-injection prompt payload.
    3. Executes local inference via Ollama HTTP API.
    4. Validates JSON schema and verifies evidence citations.
    5. Returns typed AIAnalysisReport.
    """

    def __init__(self, ollama_client: Optional[LocalOllamaClient] = None):
        self.client = ollama_client or LocalOllamaClient()

    def analyze(
        self,
        inspection: InspectionResult,
        max_evidence_count: int = 50,
        temperature: float = 0.1,
    ) -> AIAnalysisReport:
        """Execute full three-part analysis operation."""
        # Step 1: Prepare bounded evidence map
        evidence_map, serialized_evidence = prepare_bounded_evidence_index(
            inspection=inspection,
            max_evidence_count=max_evidence_count,
        )

        # Step 2: Build isolated prompt payload
        prompt = build_analysis_payload(inspection, serialized_evidence)

        # Step 3: Run inference
        raw_output = self.client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_INSTRUCTION,
            temperature=temperature,
        )

        # Step 4: Parse JSON
        parsed_json = parse_and_clean_json(raw_output)

        # Step 5: Validate schema and resolve citations
        report = build_validated_report(
            raw_data=parsed_json,
            evidence_map=evidence_map,
            inspection=inspection,
            model_name=self.client.model_name,
            endpoint=self.client.base_url,
        )

        return report
