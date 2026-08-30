"""Small OpenRouter adapter that preserves untouched provider responses."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from eval_those_models.planning import PlannedCase


class OpenRouterError(RuntimeError):
    """An HTTP, transport, or response-shape failure."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        transient: bool = False,
        raw_response: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.transient = transient
        self.raw_response = raw_response


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]: ...


class UrllibTransport:
    """Default synchronous HTTP transport."""

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except urllib.error.URLError as exc:
            raise OpenRouterError(
                f"OpenRouter transport error: {exc.reason}", transient=True
            ) from exc


@dataclass(frozen=True)
class GenerationResult:
    generation_id: str | None
    model_returned: str | None
    provider_actual: str | None
    output_text: str
    finish_reason: str | None
    usage: dict[str, Any]
    raw_response: dict[str, Any]


class OpenRouterClient:
    """OpenRouter implementation of the provider contract."""

    def __init__(
        self,
        api_key: str,
        *,
        transport: Transport | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 120,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key cannot be empty")
        self._api_key = api_key
        self._transport = transport or UrllibTransport()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_models(self) -> dict[str, Any]:
        return self._request_json("GET", "/models", None)

    def list_model_endpoints(self, model_id: str) -> dict[str, Any]:
        encoded_id = urllib.parse.quote(model_id, safe="/")
        return self._request_json("GET", f"/models/{encoded_id}/endpoints", None)

    def estimate(self, case: dict[str, Any]) -> dict[str, Any]:
        return {
            "input_tokens": case["estimated_input_tokens"],
            "output_tokens": case["estimated_output_tokens"],
            "cost_usd": case["estimated_cost_usd"],
        }

    def build_request(self, case: PlannedCase) -> dict[str, Any]:
        return {
            "model": case.model_requested,
            "messages": [{"role": "user", "content": case.rendered_prompt}],
            **case.parameters,
            "provider": case.provider_policy,
        }

    def generate(self, case: PlannedCase) -> GenerationResult:
        raw = self._request_json("POST", "/chat/completions", self.build_request(case))
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise OpenRouterError("OpenRouter response did not contain a choice", raw_response=raw)
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OpenRouterError(
                "OpenRouter response did not contain text content", raw_response=raw
            )
        usage = raw.get("usage")
        return GenerationResult(
            generation_id=raw.get("id") if isinstance(raw.get("id"), str) else None,
            model_returned=raw.get("model") if isinstance(raw.get("model"), str) else None,
            provider_actual=raw.get("provider") if isinstance(raw.get("provider"), str) else None,
            output_text=message["content"],
            finish_reason=(
                choice.get("finish_reason")
                if isinstance(choice.get("finish_reason"), str)
                else None
            ),
            usage=usage if isinstance(usage, dict) else {},
            raw_response=raw,
        )

    def get_generation_metadata(self, generation_id: str) -> dict[str, Any] | None:
        response = self._request_json("GET", f"/generation?id={generation_id}", None)
        data = response.get("data")
        return data if isinstance(data, dict) else None

    def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        status, response_body = self._transport.request(
            method, f"{self._base_url}{path}", headers, body, self._timeout
        )
        try:
            decoded = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OpenRouterError(
                f"OpenRouter returned non-JSON content with HTTP {status}",
                status_code=status,
                transient=status in {408, 409, 429, 500, 502, 503, 504},
            ) from exc
        if not 200 <= status < 300:
            detail = decoded.get("error", decoded) if isinstance(decoded, dict) else decoded
            raise OpenRouterError(
                f"OpenRouter HTTP {status}: {detail}",
                status_code=status,
                transient=status in {408, 409, 429, 500, 502, 503, 504},
            )
        if not isinstance(decoded, dict):
            raise OpenRouterError("OpenRouter returned a non-object JSON response")
        return decoded
