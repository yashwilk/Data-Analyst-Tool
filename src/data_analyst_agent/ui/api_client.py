"""The ONLY module in ui/ that imports httpx -- everything else renders.

Auth: the backend issues a JWT on register/login; every subsequent call
takes that token and sends it as `Authorization: Bearer <token>`. The
token is kept in `st.session_state`, never in a static config value.
"""

from __future__ import annotations

from typing import Any, TypedDict

import httpx

from data_analyst_agent.config.ui_config import get_ui_settings
from data_analyst_agent.ui.exceptions import BackendUnavailableError


class ApiCallResult(TypedDict):
    success: bool
    data: dict | None
    error: str | None


def _headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _client() -> httpx.Client:
    settings = get_ui_settings()
    return httpx.Client(base_url=settings.api_base_url, timeout=settings.request_timeout)


def check_health() -> bool:
    try:
        with _client() as client:
            response = client.get("/health")
            return response.status_code == 200
    except httpx.RequestError:
        return False


def _request(method: str, path: str, *, json: dict | None = None, token: str | None = None) -> ApiCallResult:
    try:
        with _client() as client:
            response = client.request(method, path, json=json, headers=_headers(token))
    except httpx.RequestError as exc:
        raise BackendUnavailableError(str(exc)) from exc

    if response.status_code >= 400:
        detail = response.json().get("detail", response.text) if response.content else response.text
        return ApiCallResult(success=False, data=None, error=str(detail))
    return ApiCallResult(success=True, data=response.json(), error=None)


def register(email: str, password: str) -> ApiCallResult:
    return _request("POST", "/api/v1/auth/register", json={"email": email, "password": password})


def login(email: str, password: str) -> ApiCallResult:
    return _request("POST", "/api/v1/auth/login", json={"email": email, "password": password})


def call_chat(question: str, conversation_id: str | None, token: str) -> ApiCallResult:
    return _request(
        "POST",
        "/api/v1/chat",
        json={"question": question, "conversation_id": conversation_id},
        token=token,
    )


def call_research(question: str, token: str) -> ApiCallResult:
    return _request("POST", "/api/v1/research", json={"question": question}, token=token)


def get_dataset_schema(token: str) -> dict[str, Any] | None:
    try:
        with _client() as client:
            response = client.get("/api/v1/dataset/schema", headers=_headers(token))
            return response.json() if response.status_code == 200 else None
    except httpx.RequestError:
        return None
