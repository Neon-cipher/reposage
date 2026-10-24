import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional


class OllamaClient:
    """Client for querying the local Ollama HTTP API with safety timeouts and error handling."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout_seconds: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def check_health(self) -> Dict[str, Any]:
        """Check if local Ollama daemon is running and retrieve installed models."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RepoSage/1.0"})
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return {"status": "ok", "models": models}
        except Exception as e:
            return {"status": "error", "error": str(e), "models": []}
        return {"status": "error", "error": "Unknown error", "models": []}

    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Execute completion request against Ollama's /api/generate endpoint.
        Returns generated text.
        """
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "RepoSage/1.0"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    return body.get("response", "").strip()
                else:
                    raise RuntimeError(f"Ollama returned HTTP status {resp.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Failed to communicate with local Ollama at {self.base_url}: {e.reason}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Ollama inference error: {str(e)}") from e
