"""DeepEval GEval backed by the local Ollama model."""
from __future__ import annotations

import asyncio
import os
import requests
from deepeval.models.base_model import DeepEvalBaseLLM

class OllamaJudge(DeepEvalBaseLLM):
    def __init__(self, model: str | None = None, timeout: int = 120):
        self.model = model or os.getenv("HW10_JUDGE_MODEL", "qwen3:8b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.timeout = timeout

    def load_model(self):
        return self

    def get_model_name(self):
        return f"Ollama/{self.model}"

    def _call(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False,
                  "think": False, "options": {"temperature": 0}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")

    def generate(self, prompt: str, schema=None):
        text = self._call(prompt)
        if schema is not None:
            return schema.model_validate_json(text)
        return text

    async def a_generate(self, prompt: str, schema=None):
        return await asyncio.to_thread(self.generate, prompt, schema)
