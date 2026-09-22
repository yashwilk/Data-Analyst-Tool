from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Contract every LLM backend must satisfy.

    Swapping providers (Groq -> Ollama -> anything else) is a new
    `services/llm_provider_*.py` file plus one branch in
    `services/llm_factory.py` -- no changes to nodes/graph/application code.
    """

    @abstractmethod
    async def generate_json(self, prompt: str) -> dict:
        """Send `prompt`, return the model's response parsed as a dict."""
        raise NotImplementedError
