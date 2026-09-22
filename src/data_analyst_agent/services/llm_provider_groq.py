"""Groq-backed LLM provider.

Same shape as the reference project's provider classes: retry with
exponential backoff, then a circuit breaker around the whole call, then
tolerant JSON extraction (LLMs wrap JSON in prose/code fences more often
than not, especially smaller/faster models like Groq's).
"""

from __future__ import annotations

import json
import logging
import re

from langchain.chat_models import init_chat_model
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.reliability.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text).strip()


def _extract_json_candidate(text: str) -> str:
    cleaned = _strip_code_fences(text)
    match = _JSON_OBJECT_RE.search(cleaned)
    return match.group(0) if match else cleaned


class GroqLLMProvider(LLMProvider):
    def __init__(self, config: dict) -> None:
        self._model = init_chat_model(
            config["model"],
            model_provider="groq",
            api_key=config["api_key"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )
        self._breaker = get_circuit_breaker("groq")
        self._max_retries = config["max_retries"]

    async def generate_json(self, prompt: str) -> dict:
        # Retry covers the *whole* round trip (call + parse), not just the
        # network call: a malformed/truncated JSON response is a fault worth
        # retrying too (a fresh completion often succeeds where the previous
        # one got cut off or mis-escaped a quote), and previously it wasn't
        # retried at all -- LLM_MAX_RETRIES was only ever exercised by
        # network errors.
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def _call_and_parse() -> dict:
            response = await self._model.ainvoke(prompt)
            content = response.content
            raw_text = content if isinstance(content, str) else str(content)

            candidate = _extract_json_candidate(raw_text)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "LLM did not return valid JSON (%s), len=%d, raw=%r",
                    exc,
                    len(raw_text),
                    raw_text,
                )
                raise ValueError(f"LLM response was not valid JSON: {exc}") from exc

        return await self._breaker.call(_call_and_parse)
