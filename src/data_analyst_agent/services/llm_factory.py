from __future__ import annotations

from data_analyst_agent.config.llm_config import get_llm_config
from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.services.llm_provider_groq import GroqLLMProvider


def get_llm_provider() -> LLMProvider:
    config = get_llm_config()
    if config["provider"] == "groq":
        return GroqLLMProvider(config)
    raise ValueError(f"Unsupported LLM provider: {config['provider']}")
