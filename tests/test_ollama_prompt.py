"""Tests for Ollama client and prompt builder."""
import json
from unittest.mock import patch, MagicMock
from reposage.ollama_client import OllamaClient
from reposage.prompts import build_analysis_prompt
from reposage.models import RepoFacts, CodeCitation, TodoItem
from reposage.reporter import _clean_and_parse_json


def test_ollama_client_health_mock():
    client = OllamaClient(base_url="http://mock-ollama:11434")
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"models": [{"name": "qwen2.5:latest"}]}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        health = client.check_health()
        assert health["status"] == "ok"
        assert "qwen2.5:latest" in health["models"]


def test_prompt_builder_structure():
    facts = RepoFacts(
        root_path="/repo",
        total_files_scanned=2,
        total_lines=100,
        has_readme=True,
        readme_path="README.md",
        todos=[TodoItem(file_path="main.py", line_number=10, tag="TODO", text="implement auth")],
        entrypoints=[CodeCitation(file_path="main.py", start_line=20, end_line=22, snippet="if __name__ == '__main__':")],
    )
    samples = {"main.py": "def foo(): pass"}
    prompt = build_analysis_prompt(facts, samples)

    assert "<<<BEGIN_UNTRUSTED_REPOSITORY_DATA>>>" in prompt
    assert "<<<END_UNTRUSTED_REPOSITORY_DATA>>>" in prompt
    assert "implement auth" in prompt
    assert "README.md" in prompt


def test_clean_and_parse_json():
    # Markdown wrapped
    raw = '```json\n{"summary_overview": "test summary", "findings": []}\n```'
    parsed = _clean_and_parse_json(raw)
    assert parsed is not None
    assert parsed["summary_overview"] == "test summary"

    # Embedded in conversational filler
    raw_with_text = 'Here is your response:\n{"summary_overview": "valid json"}\nHope that helps!'
    parsed2 = _clean_and_parse_json(raw_with_text)
    assert parsed2 is not None
    assert parsed2["summary_overview"] == "valid json"
