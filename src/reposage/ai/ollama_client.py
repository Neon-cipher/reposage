import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple


class OllamaConfigurationError(Exception):
    """Raised when Ollama configuration is invalid or the model is missing."""
    pass


class OllamaConnectionError(Exception):
    """Raised when unable to reach the local Ollama HTTP endpoint."""
    pass


class OllamaInferenceError(Exception):
    """Raised when Ollama returns an error or inference fails."""
    pass


def get_ollama_endpoint() -> str:
    """Read OLLAMA_URL from environment with default http://localhost:11434."""
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").strip()
    return url.rstrip("/")


def get_configured_model() -> str:
    """Read OLLAMA_MODEL from environment with default qwen2.5:latest."""
    return os.environ.get("OLLAMA_MODEL", "qwen2.5:latest").strip()


class LocalOllamaClient:
    """
    Dedicated local Ollama HTTP API client.
    - Connects strictly to the configured local endpoint (never switches to cloud).
    - Verifies model installation before running inference.
    - Prevents false model claims (e.g., claiming Gemma 4 or another model unless verified).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: int = 120,
    ):
        self.base_url = (base_url or get_ollama_endpoint()).rstrip("/")
        self.model_name = model_name or get_configured_model()
        self.timeout_seconds = timeout_seconds

    def check_connection(self) -> Dict[str, Any]:
        """Verify connectivity to local Ollama HTTP server."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "RepoSage-LocalAI/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    installed_models = [
                        m.get("name") for m in data.get("models", []) if m.get("name")
                    ]
                    return {"connected": True, "installed_models": installed_models}
                raise OllamaConnectionError(f"Ollama server returned HTTP status {response.status}")
        except urllib.error.URLError as e:
            raise OllamaConnectionError(
                f"Cannot connect to local Ollama at {self.base_url}. Ensure 'ollama serve' is running. Error: {e.reason}"
            ) from e
        except Exception as e:
            raise OllamaConnectionError(f"Error querying Ollama endpoint: {str(e)}") from e

    def verify_model_installed(self) -> bool:
        """
        Check that self.model_name is genuinely installed in the local Ollama instance.
        Never silently switches models or assumes a model exists.
        """
        conn_info = self.check_connection()
        installed = conn_info.get("installed_models", [])
        
        # Check direct or tag match (e.g. "qwen2.5" matching "qwen2.5:latest")
        for m in installed:
            if m == self.model_name:
                return True
            if ":" in m and m.split(":")[0] == self.model_name:
                return True
            if ":" not in self.model_name and m.startswith(f"{self.model_name}:"):
                return True

        raise OllamaConfigurationError(
            f"Configured model '{self.model_name}' is not installed in local Ollama at {self.base_url}. "
            f"Installed models: {installed}. Run 'ollama run {self.model_name}' first."
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Send raw inference prompt to Ollama /api/generate.
        Enforces verified model presence, request timeout, and error handling.
        """
        # Ensure model is verified
        self.verify_model_installed()

        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "RepoSage-LocalAI/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise OllamaInferenceError(f"Ollama returned HTTP {response.status}")
                res_body = json.loads(response.read().decode("utf-8"))
                return res_body.get("response", "").strip()
        except urllib.error.URLError as e:
            raise OllamaConnectionError(f"Connection lost during inference to {self.base_url}: {e.reason}") from e
        except Exception as e:
            raise OllamaInferenceError(f"Inference execution failed: {str(e)}") from e
