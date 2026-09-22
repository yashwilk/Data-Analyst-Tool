from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Contract every LLM backend must satisfy.

    """

    @abstractmethod
    async def generate_json(self, prompt: str) -> dict:
        """Send `prompt`, return the model's response parsed as a dict."""
        raise NotImplementedError
