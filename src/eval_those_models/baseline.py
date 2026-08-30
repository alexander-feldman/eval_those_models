"""Immutable matching of completed baseline attempts to later experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_those_models.config import ExperimentConfig, ModelConfig
from eval_those_models.storage import read_events


class BaselineMatchError(ValueError):
    """Raised when a baseline artifact cannot be matched unambiguously."""


@dataclass(frozen=True)
class BaselineMatch:
    recipe_id: str
    model_id: str
    prompt_id: str
    prompt_version: str
    attempt_id: str | None
    provider_actual: str | None
    finish_reason: str | None
    eligibility: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "model_id": self.model_id,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "attempt_id": self.attempt_id,
            "provider_actual": self.provider_actual,
            "finish_reason": self.finish_reason,
            "eligibility": self.eligibility,
        }


def match_baseline(
    config: ExperimentConfig,
    event_path: Path,
    *,
    recipe_ids: tuple[str, ...],
    model_ids: tuple[str, ...],
    prompt_id: str = "neutral-recall",
) -> tuple[BaselineMatch, ...]:
    """Match one terminal baseline attempt for every requested recipe-model unit."""
    events = read_events(event_path)
    completed = [event for event in events if event.get("event") == "run_completed"]
    if len(completed) != 1:
        raise BaselineMatchError("baseline event log must contain exactly one run_completed event")
    prompts = [prompt for prompt in config.prompts if prompt.prompt_id == prompt_id]
    if len(prompts) != 1:
        raise BaselineMatchError(f"baseline config must contain exactly one {prompt_id!r} prompt")
    prompt = prompts[0]
    model_by_id = {model.model_id: model for model in config.models}
    unknown_models = set(model_ids) - model_by_id.keys()
    if unknown_models:
        raise BaselineMatchError(f"models absent from baseline config: {sorted(unknown_models)}")
    unknown_recipes = set(recipe_ids) - set(config.recipe_ids)
    if unknown_recipes:
        raise BaselineMatchError(f"recipes absent from baseline config: {sorted(unknown_recipes)}")

    starts = {
        event["attempt_id"]: event
        for event in events
        if event.get("event") == "attempt_started" and isinstance(event.get("attempt_id"), str)
    }
    terminals: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        attempt_id = event.get("attempt_id")
        if event.get("event") in {"attempt_succeeded", "attempt_failed"} and isinstance(
            attempt_id, str
        ):
            terminals.setdefault(attempt_id, []).append(event)

    matches: list[BaselineMatch] = []
    for recipe_id in recipe_ids:
        for model_id in model_ids:
            candidates = [
                (attempt_id, start)
                for attempt_id, start in starts.items()
                if _is_candidate(start.get("case"), recipe_id, model_id, prompt_id, prompt.version)
            ]
            if len(candidates) > 1:
                raise BaselineMatchError(
                    f"multiple baseline attempts match {recipe_id}, {model_id}, {prompt_id}"
                )
            if not candidates:
                matches.append(
                    BaselineMatch(
                        recipe_id,
                        model_id,
                        prompt_id,
                        prompt.version,
                        None,
                        None,
                        None,
                        "missing",
                    )
                )
                continue
            attempt_id, start = candidates[0]
            terminal_rows = terminals.get(attempt_id, [])
            if len(terminal_rows) != 1:
                raise BaselineMatchError(
                    f"attempt {attempt_id} lacks one unambiguous terminal event"
                )
            terminal = terminal_rows[0]
            eligibility = _eligibility(start["case"], terminal, model_by_id[model_id])
            matches.append(
                BaselineMatch(
                    recipe_id,
                    model_id,
                    prompt_id,
                    prompt.version,
                    attempt_id,
                    terminal.get("provider_actual"),
                    terminal.get("finish_reason"),
                    eligibility,
                )
            )
    return tuple(matches)


def _is_candidate(
    case: Any,
    recipe_id: str,
    model_id: str,
    prompt_id: str,
    prompt_version: str,
) -> bool:
    return isinstance(case, dict) and (
        case.get("recipe_id"),
        case.get("model_requested"),
        case.get("prompt_template_id"),
        case.get("prompt_template_version"),
    ) == (recipe_id, model_id, prompt_id, prompt_version)


def _eligibility(case: dict[str, Any], terminal: dict[str, Any], model: ModelConfig) -> str:
    if terminal.get("event") != "attempt_succeeded":
        return "operational_failure"
    if terminal.get("finish_reason") != "stop":
        return "ineligible_finish_reason"
    provider_actual = terminal.get("provider_actual")
    if not isinstance(provider_actual, str) or not any(
        provider_actual.casefold() == provider.casefold() for provider in model.routing.only
    ):
        return "provider_mismatch"
    if case.get("provider_policy") != _provider_policy(model):
        return "provider_policy_mismatch"
    if case.get("parameters") != _parameters(model):
        return "parameter_mismatch"
    return "eligible"


def _provider_policy(model: ModelConfig) -> dict[str, Any]:
    return {
        "only": list(model.routing.only),
        "allow_fallbacks": model.routing.allow_fallbacks,
        "data_collection": model.routing.data_collection,
        "zdr": model.routing.zdr,
    }


def _parameters(model: ModelConfig) -> dict[str, Any]:
    result: dict[str, Any] = {"max_tokens": model.max_output_tokens}
    if model.reasoning_enabled is not None:
        result["reasoning"] = {"enabled": model.reasoning_enabled}
    if model.temperature is not None:
        result["temperature"] = model.temperature
    if model.seed is not None:
        result["seed"] = model.seed
    return result
