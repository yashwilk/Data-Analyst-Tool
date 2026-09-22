"""LLM provider configuration.

Only Groq (free-tier) is wired up for this exercise. The provider is still
read from an env var and dispatched through `services/llm_factory.py`, so
adding a second provider (e.g. Ollama) later is a new file + one branch,
not a rewrite -- same trade-off the reference project makes.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def get_llm_config() -> dict:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
    # Research answers are a full markdown report *plus* key_findings/citations
    # all inside one JSON completion -- 2048 was cutting that off mid-array,
    # producing invalid JSON. Cost/latency are billed on tokens actually
    # generated, not this cap, so headroom here is free for the (short) chat
    # answers that never approach it.
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "6000"))

    if provider != "groq":
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Only 'groq' is implemented."
        )
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is required. Get a free key at https://console.groq.com/keys "
            "and set it in your .env file."
        )

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
        "max_retries": max_retries,
        "max_tokens": max_tokens,
    }
