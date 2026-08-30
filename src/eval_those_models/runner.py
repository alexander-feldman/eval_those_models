"""Budgeted, retry-aware execution of an immutable experiment plan."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from eval_those_models.config import ExperimentConfig, ModelConfig
from eval_those_models.planning import ExperimentPlan, PlannedCase
from eval_those_models.providers.openrouter import GenerationResult, OpenRouterError
from eval_those_models.storage import EventLog


class RunError(RuntimeError):
    """Raised when preflight checks make dispatch unsafe."""


class RunnerClient(Protocol):
    def list_models(self) -> dict[str, Any]: ...

    def list_model_endpoints(self, model_id: str) -> dict[str, Any]: ...

    def build_request(self, case: PlannedCase) -> dict[str, Any]: ...

    def generate(self, case: PlannedCase) -> GenerationResult: ...

    def get_generation_metadata(self, generation_id: str) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    run_directory: Path
    succeeded: int
    failed: int
    attempts: int
    reported_cost_usd: Decimal
    budget_exceeded: bool
    not_run: int = 0
    stop_reason: str | None = None


@dataclass(frozen=True)
class _CaseResult:
    succeeded: bool
    attempts: int
    reported_cost_usd: Decimal
    stop_reason: str | None = None


def run_experiment(
    config: ExperimentConfig,
    plan: ExperimentPlan,
    client: RunnerClient,
    artifacts_root: Path,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> RunSummary:
    """Preflight against the live catalog, then execute and durably log every attempt."""
    if plan.max_retries != config.max_retries:
        raise RunError("plan retry policy does not match the experiment configuration")
    if plan.maximum_cost_with_retries_usd > config.max_budget_usd:
        raise RunError("plan exceeds the experiment budget")
    catalog = client.list_models()
    endpoints = {
        model.model_id: client.list_model_endpoints(model.model_id) for model in config.models
    }
    _validate_preflight(config, catalog, endpoints)

    run_id = f"run_{uuid.uuid4().hex}"
    run_directory = artifacts_root / config.experiment_id / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    _write_json(run_directory / "plan.json", plan.as_dict())
    _write_json(run_directory / "catalog.json", catalog)
    _write_json(run_directory / "endpoints.json", endpoints)
    events = EventLog(run_directory / "attempts.jsonl")
    events.append(
        {
            "event": "run_started",
            "recorded_at": _now(),
            "run_id": run_id,
            "experiment_id": config.experiment_id,
            "case_count": len(plan.cases),
            "estimated_cost_usd": str(plan.estimated_cost_usd),
            "maximum_cost_with_retries_usd": str(plan.maximum_cost_with_retries_usd),
            "max_budget_usd": str(config.max_budget_usd),
        }
    )

    if any(profile.web_search is not None for profile in config.tool_profiles):
        results, stop_reason = _run_budgeted_sequentially(
            config, plan, run_id, client, events, sleep
        )
    else:
        results = _run_concurrently(config, plan, run_id, client, events, sleep)
        stop_reason = None

    reported_cost = sum((result.reported_cost_usd for result in results), Decimal())
    summary = RunSummary(
        run_id=run_id,
        run_directory=run_directory,
        succeeded=sum(result.succeeded for result in results),
        failed=sum(not result.succeeded for result in results),
        attempts=sum(result.attempts for result in results),
        reported_cost_usd=reported_cost,
        budget_exceeded=reported_cost > config.max_budget_usd,
        not_run=len(plan.cases) - len(results),
        stop_reason=stop_reason,
    )
    events.append(
        {
            "event": "run_completed",
            "recorded_at": _now(),
            "run_id": run_id,
            "succeeded": summary.succeeded,
            "failed": summary.failed,
            "attempts": summary.attempts,
            "reported_cost_usd": str(summary.reported_cost_usd),
            "budget_exceeded": summary.budget_exceeded,
            "not_run": summary.not_run,
            "stop_reason": summary.stop_reason,
        }
    )
    return summary


def _run_budgeted_sequentially(
    config: ExperimentConfig,
    plan: ExperimentPlan,
    run_id: str,
    client: RunnerClient,
    events: EventLog,
    sleep: Callable[[float], None],
) -> tuple[list[_CaseResult], str | None]:
    """Reserve each search case against actual prior spend before dispatch."""
    results: list[_CaseResult] = []
    reported_cost = Decimal()
    for index, case in enumerate(plan.cases):
        reservation = case.estimated_cost_usd * (config.max_retries + 1)
        if reported_cost + reservation > config.max_budget_usd:
            reason = (
                f"reported cost ${reported_cost} plus next reservation ${reservation} "
                f"would exceed budget ${config.max_budget_usd}"
            )
            _record_stop(events, run_id, case.case_id, reason)
            return results, reason
        result = _run_case(case, run_id, config.max_retries, client, events, sleep)
        results.append(result)
        reported_cost += result.reported_cost_usd
        if result.stop_reason is not None:
            _record_stop(events, run_id, None, result.stop_reason)
            return results, result.stop_reason
        if index + 1 < len(
            plan.cases
        ) and result.reported_cost_usd > case.estimated_cost_usd * Decimal("1.25"):
            reason = (
                f"case {case.case_id} reported ${result.reported_cost_usd}, more than "
                f"125% of its ${case.estimated_cost_usd} estimate"
            )
            _record_stop(events, run_id, None, reason)
            return results, reason
    return results, None


def _run_concurrently(
    config: ExperimentConfig,
    plan: ExperimentPlan,
    run_id: str,
    client: RunnerClient,
    events: EventLog,
    sleep: Callable[[float], None],
) -> list[_CaseResult]:
    results: list[_CaseResult] = []
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = {
            executor.submit(
                _run_case, case, run_id, config.max_retries, client, events, sleep
            ): case.case_id
            for case in plan.cases
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:  # defensive: retain a terminal record for worker bugs
                events.append(
                    {
                        "event": "case_internal_error",
                        "recorded_at": _now(),
                        "run_id": run_id,
                        "case_id": futures[future],
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                results.append(_CaseResult(False, 0, Decimal()))
    return results


def _record_stop(events: EventLog, run_id: str, next_case_id: str | None, reason: str) -> None:
    events.append(
        {
            "event": "run_stopped",
            "recorded_at": _now(),
            "run_id": run_id,
            "next_case_id": next_case_id,
            "reason": reason,
        }
    )


def _run_case(
    case: PlannedCase,
    run_id: str,
    max_retries: int,
    client: RunnerClient,
    events: EventLog,
    sleep: Callable[[float], None],
) -> _CaseResult:
    retry_of: str | None = None
    cumulative_cost = Decimal()
    for attempt_number in range(1, max_retries + 2):
        attempt_id = f"attempt_{uuid.uuid4().hex}"
        started_at = _now()
        events.append(
            {
                "event": "attempt_started",
                "recorded_at": started_at,
                "run_id": run_id,
                "attempt_id": attempt_id,
                "retry_of_attempt_id": retry_of,
                "attempt_number": attempt_number,
                "case": case.as_dict(),
                "request": client.build_request(case),
            }
        )
        monotonic_started = time.monotonic()
        try:
            result = client.generate(case)
            metadata, metadata_error = _metadata(client, result)
            reported_cost = _reported_cost(result, metadata)
            cumulative_cost += reported_cost
            terminal_error = _terminal_error(case, result)
            if terminal_error is not None:
                events.append(
                    {
                        "event": "attempt_failed",
                        "recorded_at": _now(),
                        "run_id": run_id,
                        "attempt_id": attempt_id,
                        "case_id": case.case_id,
                        "started_at": started_at,
                        "latency_ms": round((time.monotonic() - monotonic_started) * 1000, 3),
                        "error_type": "NonterminalToolResponse",
                        "error": terminal_error,
                        "transient": False,
                        "will_retry": False,
                        "finish_reason": result.finish_reason,
                        "usage": result.usage,
                        "reported_cost_usd": str(reported_cost),
                        "generation_metadata": metadata,
                        "generation_metadata_error": metadata_error,
                        "raw_response": result.raw_response,
                    }
                )
                return _CaseResult(False, attempt_number, cumulative_cost, terminal_error)
            events.append(
                {
                    "event": "attempt_succeeded",
                    "recorded_at": _now(),
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "case_id": case.case_id,
                    "started_at": started_at,
                    "latency_ms": round((time.monotonic() - monotonic_started) * 1000, 3),
                    "generation_id": result.generation_id,
                    "model_requested": case.model_requested,
                    "model_returned": result.model_returned,
                    "provider_policy_requested": case.provider_policy,
                    "provider_actual": (metadata or {}).get("provider_name")
                    or result.provider_actual,
                    "parameters_requested": case.parameters,
                    "output_text": result.output_text,
                    "finish_reason": result.finish_reason,
                    "usage": result.usage,
                    "reported_cost_usd": str(reported_cost),
                    "generation_metadata": metadata,
                    "generation_metadata_error": metadata_error,
                    "raw_response": result.raw_response,
                }
            )
            return _CaseResult(True, attempt_number, cumulative_cost)
        except OpenRouterError as exc:
            reported_cost = _raw_response_cost(exc.raw_response)
            cumulative_cost += reported_cost
            will_retry = exc.transient and attempt_number <= max_retries
            events.append(
                {
                    "event": "attempt_failed",
                    "recorded_at": _now(),
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "case_id": case.case_id,
                    "started_at": started_at,
                    "latency_ms": round((time.monotonic() - monotonic_started) * 1000, 3),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "status_code": exc.status_code,
                    "transient": exc.transient,
                    "will_retry": will_retry,
                    "raw_response": exc.raw_response,
                    "reported_cost_usd": str(reported_cost),
                }
            )
            if not will_retry:
                return _CaseResult(False, attempt_number, cumulative_cost)
            retry_of = attempt_id
            sleep(2 ** (attempt_number - 1))
    raise AssertionError("retry loop did not return")


def _metadata(
    client: RunnerClient, result: GenerationResult
) -> tuple[dict[str, Any] | None, str | None]:
    if result.generation_id is None:
        return None, None
    try:
        return client.get_generation_metadata(result.generation_id), None
    except OpenRouterError as exc:
        return None, str(exc)


def _reported_cost(result: GenerationResult, metadata: dict[str, Any] | None) -> Decimal:
    candidates = [result.usage.get("cost")]
    if metadata is not None:
        candidates.extend([metadata.get("total_cost"), metadata.get("usage")])
    for value in candidates:
        if isinstance(value, bool) or value is None:
            continue
        try:
            return Decimal(str(value))
        except InvalidOperation:
            continue
    return Decimal()


def _raw_response_cost(raw_response: dict[str, Any] | None) -> Decimal:
    if not isinstance(raw_response, dict):
        return Decimal()
    usage = raw_response.get("usage")
    if not isinstance(usage, dict):
        return Decimal()
    try:
        return Decimal(str(usage.get("cost", 0)))
    except InvalidOperation:
        return Decimal()


def _terminal_error(case: PlannedCase, result: GenerationResult) -> str | None:
    if result.finish_reason == "tool_calls":
        return "response ended with nonterminal tool_calls finish reason"
    configured_limit = _configured_search_limit(case)
    if configured_limit is None:
        return None
    details = result.usage.get("server_tool_use_details")
    if not isinstance(details, dict):
        return None
    counts = [details.get("web_search_requests"), details.get("tool_calls_executed")]
    observed = max((value for value in counts if isinstance(value, int)), default=0)
    if observed > configured_limit:
        return (
            f"response reported {observed} search calls above configured limit {configured_limit}"
        )
    return None


def _configured_search_limit(case: PlannedCase) -> int | None:
    tools = case.parameters.get("tools")
    if not isinstance(tools, list) or not tools:
        return None
    value = case.parameters.get("max_tool_calls")
    return value if isinstance(value, int) else None


def _validate_preflight(
    config: ExperimentConfig,
    catalog: dict[str, Any],
    endpoint_snapshots: dict[str, dict[str, Any]],
) -> None:
    rows = catalog.get("data")
    if not isinstance(rows, list):
        raise RunError("OpenRouter catalog response has no model list")
    by_id = {
        row.get("id"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    for model in config.models:
        row = by_id.get(model.model_id)
        if row is None:
            raise RunError(f"configured model is absent from the live catalog: {model.model_id}")
        snapshot = endpoint_snapshots[model.model_id]
        data = snapshot.get("data")
        endpoint_rows = data.get("endpoints") if isinstance(data, dict) else None
        if not isinstance(endpoint_rows, list):
            raise RunError(f"OpenRouter returned no endpoint list for {model.model_id}")
        for provider in model.routing.only:
            matches = [
                endpoint
                for endpoint in endpoint_rows
                if isinstance(endpoint, dict)
                and str(endpoint.get("provider_name", "")).casefold() == provider.casefold()
                and endpoint.get("status") == 0
            ]
            if not matches:
                raise RunError(
                    f"no available {provider} endpoint exists for configured model {model.model_id}"
                )
            for endpoint in matches:
                _validate_endpoint(
                    model,
                    provider,
                    endpoint,
                    web_search_enabled=any(
                        profile.web_search is not None for profile in config.tool_profiles
                    ),
                    native_search_required=any(
                        profile.web_search is not None and profile.web_search.engine == "native"
                        for profile in config.tool_profiles
                    ),
                )


def _validate_endpoint(
    model: ModelConfig,
    provider: str,
    endpoint: dict[str, Any],
    *,
    web_search_enabled: bool,
    native_search_required: bool,
) -> None:
    pricing = endpoint.get("pricing")
    if not isinstance(pricing, dict):
        raise RunError(f"live {provider} endpoint has no pricing for {model.model_id}")
    live_input = _per_million(pricing.get("prompt"), model.model_id, "input")
    live_output = _per_million(pricing.get("completion"), model.model_id, "output")
    if live_input > model.pricing_ceiling.input_per_million:
        raise RunError(
            f"live {provider} input price for {model.model_id} (${live_input}/M) exceeds "
            f"configured ceiling (${model.pricing_ceiling.input_per_million}/M)"
        )
    if live_output > model.pricing_ceiling.output_per_million:
        raise RunError(
            f"live {provider} output price for {model.model_id} (${live_output}/M) exceeds "
            f"configured ceiling (${model.pricing_ceiling.output_per_million}/M)"
        )
    if web_search_enabled:
        if pricing.get("web_search") is None:
            if native_search_required:
                raise RunError(
                    f"live {provider} endpoint does not expose verifiable web-search pricing "
                    f"for {model.model_id}"
                )
        else:
            try:
                live_search = Decimal(str(pricing["web_search"]))
            except InvalidOperation as exc:
                raise RunError(
                    f"live {provider} endpoint has invalid web-search pricing for {model.model_id}"
                ) from exc
            if live_search > model.pricing_ceiling.web_search_per_request:
                raise RunError(
                    f"live {provider} web-search price for {model.model_id} (${live_search}) "
                    f"exceeds configured ceiling "
                    f"(${model.pricing_ceiling.web_search_per_request})"
                )
    supported = endpoint.get("supported_parameters")
    if isinstance(supported, list):
        requested = {"max_tokens"}
        if model.reasoning_enabled is not None:
            requested.add("reasoning")
        if web_search_enabled:
            requested.add("tools")
        if model.temperature is not None:
            requested.add("temperature")
        if model.seed is not None:
            requested.add("seed")
        unsupported = requested - set(supported)
        if unsupported:
            raise RunError(
                f"live {provider} endpoint for {model.model_id} does not support requested "
                f"parameters: {sorted(unsupported)}"
            )


def _per_million(value: Any, model_id: str, kind: str) -> Decimal:
    try:
        result = Decimal(str(value)) * Decimal(1_000_000)
    except (InvalidOperation, TypeError) as exc:
        raise RunError(f"live catalog has invalid {kind} pricing for {model_id}") from exc
    if result < 0:
        raise RunError(f"live catalog has negative {kind} pricing for {model_id}")
    return result


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _now() -> str:
    return datetime.now(UTC).isoformat()
