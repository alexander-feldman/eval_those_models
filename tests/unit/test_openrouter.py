import json
from decimal import Decimal
from typing import Any

import pytest

from eval_those_models.planning import PlannedCase
from eval_those_models.providers.openrouter import OpenRouterClient, OpenRouterError


class FakeTransport:
    def __init__(self, status: int, response: dict[str, Any]) -> None:
        self.status = status
        self.response = response
        self.requests: list[tuple[str, str, dict[str, str], bytes | None]] = []

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        self.requests.append((method, url, headers, body))
        return self.status, json.dumps(self.response).encode()


def _case() -> PlannedCase:
    return PlannedCase(
        case_id="case_1",
        experiment_id="experiment",
        recipe_id="recipe",
        rights_context="modern",
        prompt_template_id="prompt",
        prompt_template_version="1",
        rendered_prompt="Hello",
        model_requested="example/model",
        provider_policy={"only": ["Example"], "allow_fallbacks": False},
        parameters={"max_tokens": 10, "temperature": 0},
        repetition=1,
        harness_git_commit="abc",
        estimated_input_tokens=2,
        estimated_output_tokens=10,
        estimated_cost_usd=Decimal(),
    )


def test_generate_sends_controlled_request_and_preserves_raw_response() -> None:
    response = {
        "id": "generation-1",
        "model": "example/model-v1",
        "provider": "Example",
        "choices": [{"message": {"content": "Result"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "cost": 0.001},
    }
    transport = FakeTransport(200, response)
    client = OpenRouterClient("secret", transport=transport, base_url="https://example.test")

    result = client.generate(_case())

    assert result.output_text == "Result"
    assert result.raw_response == response
    method, url, headers, body = transport.requests[0]
    assert method == "POST"
    assert url == "https://example.test/chat/completions"
    assert headers["Authorization"] == "Bearer secret"
    assert json.loads(body or b"{}")["provider"]["only"] == ["Example"]


def test_http_429_is_marked_transient() -> None:
    client = OpenRouterClient(
        "secret",
        transport=FakeTransport(429, {"error": {"message": "slow down"}}),
    )

    with pytest.raises(OpenRouterError) as caught:
        client.generate(_case())

    assert caught.value.transient
    assert caught.value.status_code == 429


def test_malformed_success_response_is_rejected() -> None:
    client = OpenRouterClient("secret", transport=FakeTransport(200, {"choices": []}))

    with pytest.raises(OpenRouterError, match="choice") as caught:
        client.generate(_case())

    assert caught.value.raw_response == {"choices": []}


def test_list_model_endpoints_uses_model_path() -> None:
    transport = FakeTransport(200, {"data": {"endpoints": []}})
    client = OpenRouterClient("secret", transport=transport, base_url="https://example.test")

    client.list_model_endpoints("example/model")

    assert transport.requests[0][1] == "https://example.test/models/example/model/endpoints"
