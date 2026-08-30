from collections import defaultdict
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from eval_those_models.config import (
    ExperimentConfig,
    ModelConfig,
    PricingCeiling,
    RoutingConfig,
    ToolProfileConfig,
    WebSearchConfig,
)
from eval_those_models.planning import ExperimentPlan, PlannedCase
from eval_those_models.providers.openrouter import GenerationResult, OpenRouterError
from eval_those_models.runner import RunError, run_experiment
from eval_those_models.storage import read_events


class FakeClient:
    def __init__(self, failures: int = 0, live_output_price: str = "0.000001") -> None:
        self.failures = failures
        self.live_output_price = live_output_price
        self.calls: dict[str, int] = defaultdict(int)
        self.catalog_calls = 0

    def list_models(self) -> dict[str, Any]:
        self.catalog_calls += 1
        return {
            "data": [
                {
                    "id": "example/model",
                    "pricing": {"prompt": "0.0000005", "completion": self.live_output_price},
                }
            ]
        }

    def list_model_endpoints(self, model_id: str) -> dict[str, Any]:
        return {
            "data": {
                "endpoints": [
                    {
                        "provider_name": "Example",
                        "status": 0,
                        "pricing": {
                            "prompt": "0.0000005",
                            "completion": self.live_output_price,
                        },
                        "supported_parameters": [
                            "max_tokens",
                            "reasoning",
                            "temperature",
                            "seed",
                            "tools",
                        ],
                    }
                ]
            }
        }

    def build_request(self, case: PlannedCase) -> dict[str, Any]:
        return {"model": case.model_requested, "prompt": case.rendered_prompt}

    def generate(self, case: PlannedCase) -> GenerationResult:
        self.calls[case.case_id] += 1
        if self.calls[case.case_id] <= self.failures:
            raise OpenRouterError("rate limited", status_code=429, transient=True)
        raw = {
            "id": "generation-1",
            "model": "example/model",
            "provider": "Example",
            "choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
            "usage": {"cost": 0.001},
        }
        return GenerationResult(
            generation_id="generation-1",
            model_returned="example/model",
            provider_actual="Example",
            output_text="answer",
            finish_reason="stop",
            usage={"cost": 0.001},
            raw_response=raw,
        )

    def get_generation_metadata(self, generation_id: str) -> dict[str, Any] | None:
        return {"provider_name": "Example"}


def _config() -> ExperimentConfig:
    return ExperimentConfig(
        schema_version=1,
        experiment_id="smoke",
        recipe_ids=("recipe",),
        prompts=(),
        models=(
            ModelConfig(
                model_id="example/model",
                routing=RoutingConfig(("Example",), False, "deny", False),
                max_output_tokens=10,
                temperature=0,
                seed=0,
                reasoning_enabled=False,
                pricing_ceiling=PricingCeiling(Decimal("1"), Decimal("2")),
            ),
        ),
        repetitions=1,
        max_budget_usd=Decimal("0.02"),
        concurrency=1,
        max_retries=2,
    )


def _plan() -> ExperimentPlan:
    case = PlannedCase(
        case_id="case_1",
        experiment_id="smoke",
        recipe_id="recipe",
        rights_context="modern",
        prompt_template_id="prompt",
        prompt_template_version="1",
        rendered_prompt="hello",
        model_requested="example/model",
        provider_policy={"only": ["Example"]},
        parameters={"max_tokens": 10},
        repetition=1,
        harness_git_commit="abc",
        estimated_input_tokens=2,
        estimated_output_tokens=10,
        estimated_cost_usd=Decimal("0.001"),
    )
    return ExperimentPlan("smoke", (case,), (), Decimal("0.02"), max_retries=2)


def test_run_retries_transient_failure_and_preserves_both_attempts(tmp_path: Path) -> None:
    sleeps: list[float] = []

    summary = run_experiment(
        _config(), _plan(), FakeClient(failures=1), tmp_path, sleep=sleeps.append
    )

    assert summary.succeeded == 1
    assert summary.failed == 0
    assert summary.attempts == 2
    assert summary.reported_cost_usd == Decimal("0.001")
    assert summary.budget_exceeded is False
    assert sleeps == [1]
    events = read_events(summary.run_directory / "attempts.jsonl")
    failed = next(event for event in events if event["event"] == "attempt_failed")
    retried = [event for event in events if event["event"] == "attempt_started"][1]
    assert failed["will_retry"] is True
    assert retried["retry_of_attempt_id"] == failed["attempt_id"]
    assert events[-1]["event"] == "run_completed"


def test_run_does_not_retry_permanent_failure(tmp_path: Path) -> None:
    client = FakeClient()

    def fail(case: PlannedCase) -> GenerationResult:
        raise OpenRouterError("bad request", status_code=400, transient=False)

    client.generate = fail  # type: ignore[method-assign]
    summary = run_experiment(_config(), _plan(), client, tmp_path, sleep=lambda _: None)

    assert summary.failed == 1
    assert summary.attempts == 1


def test_run_flags_actual_cost_above_budget(tmp_path: Path) -> None:
    config = replace(_config(), max_budget_usd=Decimal("0.0005"), max_retries=0)
    case = replace(_plan().cases[0], estimated_cost_usd=Decimal("0.0001"))
    plan = ExperimentPlan("smoke", (case,), (), Decimal("0.0005"))

    summary = run_experiment(config, plan, FakeClient(), tmp_path)

    assert summary.reported_cost_usd == Decimal("0.001")
    assert summary.budget_exceeded is True
    events = read_events(summary.run_directory / "attempts.jsonl")
    assert events[-1]["budget_exceeded"] is True


def test_run_refuses_live_price_above_configured_ceiling(tmp_path: Path) -> None:
    expensive = FakeClient(live_output_price="0.000003")

    with pytest.raises(RunError, match="exceeds configured ceiling"):
        run_experiment(_config(), _plan(), expensive, tmp_path)

    assert not list(tmp_path.iterdir())


def test_run_refuses_plan_above_budget_before_catalog_request(tmp_path: Path) -> None:
    client = FakeClient()
    low_budget_config = replace(_config(), max_budget_usd=Decimal("0.0001"))

    with pytest.raises(RunError, match="exceeds the experiment budget"):
        run_experiment(low_budget_config, _plan(), client, tmp_path)

    assert client.catalog_calls == 0


def test_run_refuses_native_web_search_without_verifiable_live_price(tmp_path: Path) -> None:
    search_config = replace(
        _config(),
        tool_profiles=(ToolProfileConfig("web", WebSearchConfig("native", 1, 3, 3, 1500, 5000)),),
    )

    with pytest.raises(RunError, match="verifiable web-search pricing"):
        run_experiment(search_config, _plan(), FakeClient(), tmp_path)


def _search_config(max_budget: str = "0.02") -> ExperimentConfig:
    return replace(
        _config(),
        max_budget_usd=Decimal(max_budget),
        max_retries=0,
        tool_profiles=(ToolProfileConfig("web", WebSearchConfig("auto", 1, 3, 3, 1500, 16_000)),),
        models=(
            replace(
                _config().models[0],
                pricing_ceiling=PricingCeiling(Decimal("1"), Decimal("2"), Decimal("0.01")),
            ),
        ),
    )


def _search_plan(case_count: int = 2) -> ExperimentPlan:
    cases = tuple(
        replace(
            _plan().cases[0],
            case_id=f"case_{index}",
            tool_profile_id="web",
            parameters={
                "max_tokens": 10,
                "tools": [{"type": "openrouter:web_search"}],
                "max_tool_calls": 1,
            },
            estimated_cost_usd=Decimal("0.0005"),
        )
        for index in range(case_count)
    )
    return ExperimentPlan("smoke", cases, (), Decimal("0.02"), max_retries=0)


def test_search_run_stops_before_next_case_after_cost_drift(tmp_path: Path) -> None:
    client = FakeClient()

    summary = run_experiment(_search_config(), _search_plan(), client, tmp_path)

    assert summary.succeeded == 1
    assert summary.not_run == 1
    assert summary.stop_reason is not None
    assert "125%" in summary.stop_reason
    assert sum(client.calls.values()) == 1
    events = read_events(summary.run_directory / "attempts.jsonl")
    assert any(event["event"] == "run_stopped" for event in events)


def test_search_run_rejects_nonterminal_tool_response_and_counts_cost(tmp_path: Path) -> None:
    client = FakeClient()

    def nonterminal(case: PlannedCase) -> GenerationResult:
        return GenerationResult(
            generation_id="generation-1",
            model_returned="example/model",
            provider_actual="Example",
            output_text="searching",
            finish_reason="tool_calls",
            usage={"cost": 0.001},
            raw_response={},
        )

    client.generate = nonterminal  # type: ignore[method-assign]
    summary = run_experiment(_search_config(), _search_plan(1), client, tmp_path)

    assert summary.failed == 1
    assert summary.reported_cost_usd == Decimal("0.001")
    events = read_events(summary.run_directory / "attempts.jsonl")
    failed = next(event for event in events if event["event"] == "attempt_failed")
    assert failed["error_type"] == "NonterminalToolResponse"


def test_search_run_rejects_reported_searches_above_limit(tmp_path: Path) -> None:
    client = FakeClient()

    def over_limit(case: PlannedCase) -> GenerationResult:
        return GenerationResult(
            generation_id="generation-1",
            model_returned="example/model",
            provider_actual="Example",
            output_text="answer",
            finish_reason="stop",
            usage={
                "cost": 0.001,
                "server_tool_use_details": {"web_search_requests": 2},
            },
            raw_response={},
        )

    client.generate = over_limit  # type: ignore[method-assign]
    summary = run_experiment(_search_config(), _search_plan(1), client, tmp_path)

    assert summary.failed == 1
    assert summary.stop_reason is not None
    events = read_events(summary.run_directory / "attempts.jsonl")
    failed = next(event for event in events if event["event"] == "attempt_failed")
    assert "above configured limit" in failed["error"]


def test_search_run_does_not_dispatch_after_tool_violation(tmp_path: Path) -> None:
    client = FakeClient()

    def over_limit(case: PlannedCase) -> GenerationResult:
        client.calls[case.case_id] += 1
        return GenerationResult(
            generation_id="generation-1",
            model_returned="example/model",
            provider_actual="Example",
            output_text="answer",
            finish_reason="stop",
            usage={
                "cost": 0.0001,
                "server_tool_use_details": {"web_search_requests": 2},
            },
            raw_response={},
        )

    client.generate = over_limit  # type: ignore[method-assign]
    summary = run_experiment(_search_config(), _search_plan(2), client, tmp_path)

    assert summary.failed == 1
    assert summary.not_run == 1
    assert sum(client.calls.values()) == 1
